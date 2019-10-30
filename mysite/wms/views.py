import shlex
from datetime import datetime

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_list_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django_datatables_view.base_datatable_view import BaseDatatableView
from django_pandas.io import read_frame
from django_tables2 import SingleTableMixin

from .forms import *
from .sched import transfer_adjust, position_cal, agv_route_home, agv_route_manual
from .tables import *


def permission_denied(request):
    messages.add_message(request, messages.INFO, "You don't have authorization to view this page. Please sign in with authorized user account.")
    return redirect(request.META.get('HTTP_REFERER'))


def groups_required(*groups):
    return user_passes_test(lambda u: u.groups.filter(name__in=groups).exists() | u.is_superuser, login_url='/permission_denied/', redirect_field_name=None)


def redirect_home(request):
    return redirect('wms:dashboard')


class DashboardView(generic.TemplateView):
    template_name = 'wms/dashboard.html'

    obj = Product.objects.order_by().distinct().values_list('plant__plant_id', flat=True)

    def get_context_data(self, **kwargs):
        # production_target = '{:,}'.format(1200000)
        # current_production = '{:,}'.format(550000)
        in_stock_status = '{:,}'.format(Storage.objects.filter(have_inventory=True).aggregate(models.Sum('inv_qty'))['inv_qty__sum']
                                        if Storage.objects.filter(have_inventory=True).aggregate(models.Sum('inv_qty'))['inv_qty__sum'] is not None else 0)
        in_stock_pct = '{:.0%}'.format(Storage.objects.filter(have_inventory=True).count() / Storage.objects.all().count() if Storage.objects.all() else 0)
        agv_run = AgvTransfer.objects.filter(run=1).count()
        agv_total = AgvTransfer.objects.all().count()

        # For Overview Graph #
        overview_plant_list = list(enumerate([_('All')] + list(Product.objects.select_related('plant').order_by().distinct().values_list('plant', flat=True))))
        product_name = {}
        product_color = {}
        qty_inventory = {}
        qty_buffer = {}
        qty_misplace = {}
        qty_avail_storage = {}
        pct_qty_inventory = {}
        pct_qty_buffer = {}
        pct_qty_misplace = {}
        pct_qty_avail_storage = {}
        for i, plant in overview_plant_list:
            if plant != _('All'):
                product_name[i] = list(Product.objects.select_related('plant').filter(plant__plant_id=plant).values_list('product_name', flat=True))
                obj_list = get_list_or_404(Product, product_name__in=product_name[i])
            elif plant == _('All'):
                product_name[i] = list(Product.objects.select_related('plant').all().values_list('product_name', flat=True))
                obj_list = Product.objects.all()
            product_color[i] = [obj.bg_color for obj in obj_list]
            qty_inventory[i] = [(obj.qty_inventory if obj.qty_inventory else 0) for obj in obj_list]
            qty_buffer[i] = [(obj.qty_buffer if obj.qty_buffer else 0) for obj in obj_list]
            qty_misplace[i] = [(obj.qty_misplace if obj.qty_misplace else 0) for obj in obj_list]
            qty_avail_storage[i] = [(obj.qty_storage - obj.qty_total if obj.qty_storage else 0) for obj in obj_list]
            pct_qty_inventory[i] = [(round(obj.qty_inventory / obj.qty_storage * 100, 2) if obj.qty_storage else 0) for obj in obj_list]
            pct_qty_buffer[i] = [(round(obj.qty_buffer / obj.qty_storage * 100, 2) if obj.qty_storage else 0) for obj in obj_list]
            pct_qty_misplace[i] = [(round(obj.qty_misplace / obj.qty_storage * 100, 2) if obj.qty_storage else 0) for obj in obj_list]
            pct_qty_avail_storage[i] = [(round((obj.qty_storage - obj.qty_total) / obj.qty_storage * 100, 2) if obj.qty_storage else 0) for obj in obj_list]

        # For Usage Graph #
        qty_inventory_plant = []
        usage_plant_list = list(enumerate(list(Product.objects.order_by().distinct().values_list('plant', flat=True))))
        for i, plant in usage_plant_list:
            qty_inventory_plant.append(
                Storage.objects.filter(column_id__is_inventory=True, column_id__for_product__plant__plant_id=plant).aggregate(models.Sum('inv_qty'))['inv_qty__sum'])
            if qty_inventory_plant[-1] == None:
                qty_inventory_plant[-1] = 0

        context = super().get_context_data(**kwargs)
        context.update({
            # 'production_target': production_target,
            # 'current_production': current_production,
            'in_stock_status': in_stock_status,
            'in_stock_pct': in_stock_pct,
            'agv_run': agv_run,
            'agv_total': agv_total,
            # For Overview Graph #
            'overview_plant_list': overview_plant_list,
            'product_name': product_name,
            'product_color': product_color,
            'qty_inventory': qty_inventory,
            'qty_buffer': qty_buffer,
            'qty_misplace': qty_misplace,
            'qty_avail_storage': qty_avail_storage,
            'pct_qty_inventory': pct_qty_inventory,
            'pct_qty_buffer': pct_qty_buffer,
            'pct_qty_misplace': pct_qty_misplace,
            'pct_qty_avail_storage': pct_qty_avail_storage,
            # For Usage Graph #
            'usage_plant_list': usage_plant_list,
            'qty_inventory_plant': qty_inventory_plant,
        })
        return context


def layout_map(obj_storage, debug=False, age=False):
    layout = {}
    layout_col = []
    layout_row = []

    skips = {40, 45}
    col_range = range(31, 97)
    row_range = range(1, 21)
    for col in (x for x in col_range if x not in skips):
        layout_col.append(col)
        layout[col] = {}
        for row in row_range:
            if col == layout_col[0]:
                layout_row.append(row)
            layout[col][row] = {}

    for col in layout_col:
        for row in layout_row:
            layout[col][row]['storage_id'] = ''
            layout[col][row]['column_id'] = ''
            layout[col][row]['is_inventory'] = ''
            layout[col][row]['storage_for'] = ''
    df_product = read_frame(Product.objects.all(), index_col='product_name', verbose=False)
    for s in obj_storage:
        layout[s.layout_col][s.layout_row]['storage_id'] = s.storage_id
        layout[s.layout_col][s.layout_row]['column_id'] = s.column_id.column_id
        layout[s.layout_col][s.layout_row]['is_inventory'] = s.column_id.is_inventory
        layout[s.layout_col][s.layout_row]['storage_for'] = s.column_id.storage_for
        layout[s.layout_col][s.layout_row]['have_inventory'] = s.have_inventory
        layout[s.layout_col][s.layout_row]['misplace'] = s.misplace
        if not debug and s.have_inventory:
            layout[s.layout_col][s.layout_row]['inv_product'] = s.inv_product.product_name if s.inv_product else 'No Data'
            layout[s.layout_col][s.layout_row]['inv_qty'] = s.inv_qty
            layout[s.layout_col][s.layout_row]['lot_name'] = s.lot_name
            layout[s.layout_col][s.layout_row]['created_on'] = s.created_on
            layout[s.layout_col][s.layout_row]['updated_on'] = s.updated_on
            layout[s.layout_col][s.layout_row]['bg_color'] = s.bg_color
            layout[s.layout_col][s.layout_row]['font_color'] = s.font_color
            if age:
                layout[s.layout_col][s.layout_row]['age'] = (timezone.now() - s.created_on).days
        elif debug and s.is_inventory:
            layout[s.layout_col][s.layout_row]['bg_color'] = df_product.loc[s.column_id.storage_for, 'bg_color']
            layout[s.layout_col][s.layout_row]['font_color'] = df_product.loc[s.column_id.storage_for, 'font_color']

    header_1 = []
    footer_1 = []
    header_2 = []
    header_col = []
    footer_2 = []
    footer_col = []
    for i in range(64):

        # if divmod(i, 4)[1] == 0:
        #     if 11 - divmod(i, 4)[0] > 0:
        #         header_1.append('B{:02d}'.format(11 - divmod(i, 4)[0]))
        #     footer_1.append('A{:02d}'.format(16 - divmod(i, 4)[0]))
        #
        # if 11 - divmod(i, 4)[0] > 0:
        #     header_2.append('C{:02d}'.format(4 - divmod(i, 4)[1]))
        #     # header_2_col.append('C{:02d}'.format(4 - divmod(i, 4)[1]))
        # footer_2.append('C{:02d}'.format(4 - divmod(i, 4)[1]))

        if 11 - divmod(i, 4)[0] > 0:
            if divmod(i, 4)[1] == 0:
                header_1.append('B{:02d}'.format(11 - divmod(i, 4)[0]))
            header_2.append('C{:02d}'.format(4 - divmod(i, 4)[1]))
            header_col.append('B{:02d}C{:02d}'.format(11 - divmod(i, 4)[0], 4 - divmod(i, 4)[1]))
            zip_header_2 = zip(header_2, header_col)

        if divmod(i, 4)[1] == 0:
            footer_1.append('A{:02d}'.format(16 - divmod(i, 4)[0]))
        footer_2.append('C{:02d}'.format(4 - divmod(i, 4)[1]))
        footer_col.append('A{:02d}C{:02d}'.format(16 - divmod(i, 4)[0], 4 - divmod(i, 4)[1]))
        zip_footer_2 = zip(footer_2, footer_col)

    index = ['R{:02d}'.format(i + 1) for i in range(8)] + [''] + ['R{}'.format(11 - i) for i in range(11)]
    zip_row = zip(index, layout_row)

    return layout, header_1, zip_header_2, footer_1, zip_footer_2, layout_col, zip_row


class LayoutView(generic.TemplateView):
    template_name = 'wms/layout.html'

    def get_context_data(self, **kwargs):
        obj_storage = Storage.objects.select_related('column_id', 'column_id__for_product', 'inv_product').all()
        layout, header_1, zip_header_2, footer_1, zip_footer_2, layout_col, zip_row = layout_map(obj_storage)
        in_queue = list(set(AgvQueue.objects.all().values_list('pick_id', flat=True)) | set(AgvQueue.objects.all().values_list('place_id', flat=True)))
        transfer_db = AgvTransfer.objects.all()

        context = super().get_context_data(**kwargs)
        context.update({
            'layout': layout,
            'header_1': header_1,
            'zip_header_2': zip_header_2,
            'footer_1': footer_1,
            'zip_footer_2': zip_footer_2,
            'layout_col': layout_col,
            'zip_row': zip_row,
            'in_queue': in_queue,
            'transfer_db': transfer_db,
        })
        return context


class LayoutDebugView(generic.TemplateView):
    template_name = 'wms/layout_debug.html'

    def get_context_data(self, **kwargs):
        obj_storage = Storage.objects.select_related('column_id', 'column_id__for_product', 'inv_product').all()
        layout, header_1, zip_header_2, footer_1, zip_footer_2, layout_col, zip_row = layout_map(obj_storage, debug=True)

        context = super().get_context_data(**kwargs)
        context.update({
            'layout': layout,
            'header_1': header_1,
            'zip_header_2': zip_header_2,
            'footer_1': footer_1,
            'zip_footer_2': zip_footer_2,
            'layout_col': layout_col,
            'zip_row': zip_row,
        })
        return context


class LayoutAgeView(generic.TemplateView):
    template_name = 'wms/layout_age.html'

    def get_context_data(self, **kwargs):
        obj_storage = Storage.objects.select_related('column_id', 'column_id__for_product', 'inv_product').all()
        layout, header_1, zip_header_2, footer_1, zip_footer_2, layout_col, zip_row = layout_map(obj_storage, age=True)

        context = super().get_context_data(**kwargs)
        context.update({
            'layout': layout,
            'header_1': header_1,
            'zip_header_2': zip_header_2,
            'footer_1': footer_1,
            'zip_footer_2': zip_footer_2,
            'layout_col': layout_col,
            'zip_row': zip_row,
        })
        return context


@login_required
def inv_create(request, pk):
    obj = get_object_or_404(Storage, pk=pk)
    data = {}
    if request.method == 'POST':
        form = InventoryForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_on = obj.created_on if obj.created_on is not None else timezone.now()
            obj.updated_on = timezone.now()
            obj.changeReason = 'Manual Create Inventory'
            obj.save()
            data['form_is_valid'] = True
        else:
            data['form_is_valid'] = False
    else:
        if obj.column_id.is_inventory:
            obj.inv_product = obj.column_id.for_product
            obj.inv_qty = obj.inv_product.qty_limit if obj.inv_product else 0
        obj.created_on = timezone.now()
        form = InventoryForm(instance=obj)

    template_name = 'wms/layout/inv_create.html'
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


@login_required
def inv_update(request, pk):
    obj = get_object_or_404(Storage, pk=pk)
    data = {}
    if request.method == 'POST':
        form = InventoryForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_on = timezone.now()
            obj.changeReason = 'Manual Update Inventory'
            obj.save()
            data['form_is_valid'] = True
        else:
            data['form_is_valid'] = False
    else:
        form = InventoryForm(instance=obj)

    template_name = 'wms/layout/inv_update.html'
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


@login_required
def inv_delete(request, pk):
    obj = get_object_or_404(Storage, pk=pk)
    obj.inv_product = None
    obj.inv_qty = None
    obj.lot_name = None
    obj.created_on = None
    obj.updated_on = timezone.now()
    obj.changeReason = 'Manual Delete Inventory'
    obj.save()
    return redirect('wms:layout')


@login_required
def invcol_update(request, pk):
    qs_storage = get_object_or_404(Column, pk=pk).storage_set.all()
    data = {}
    if request.method == 'POST':
        obj = qs_storage.first()
        form = InventoryColumnForm(request.POST)
        if form.is_valid():
            for obj in qs_storage:
                if not obj.have_inventory:
                    obj.inv_product = get_object_or_404(Product, product_name=form.cleaned_data['inv_product'])
                    obj.changeReason = 'Manual Create Inventory'
                elif obj.inv_product.product_name != form.cleaned_data['inv_product']:
                    obj.inv_product = get_object_or_404(Product, product_name=form.cleaned_data['inv_product'])
                    obj.changeReason = 'Manual Update Inventory'
                obj.inv_qty = form.cleaned_data['inv_qty']
                obj.lot_name = form.cleaned_data['lot_name']
                obj.created_on = form.cleaned_data['created_on'] if form.cleaned_data['created_on'] is not None else timezone.now()
                obj.updated_on = timezone.now()
                obj.save()
            data['form_is_valid'] = True
        else:
            data['form_is_valid'] = False
    else:
        if qs_storage.filter(have_inventory=True).exists():
            obj = qs_storage.filter(have_inventory=True).first()
        else:
            obj = qs_storage.first()
            if obj.column_id.is_inventory:
                obj.inv_product = obj.column_id.for_product
                obj.inv_qty = obj.inv_product.qty_limit if obj.inv_product else 0
            obj.created_on = timezone.now()

        form_data = {
            'column_id': pk,
            'inv_product': obj.inv_product,
            'inv_qty': obj.inv_qty,
            'lot_name': obj.lot_name,
            'created_on': obj.created_on,
        }
        form = InventoryColumnForm(initial=form_data)

    template_name = 'wms/layout/invcol_update.html'
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


@login_required
def invcol_delete(request, pk):
    qs_storage = get_object_or_404(Column, pk=pk).storage_set.all()
    for obj in qs_storage:
        obj.inv_product = None
        obj.inv_qty = None
        obj.lot_name = None
        obj.created_on = None
        obj.updated_on = timezone.now()
        obj.changeReason = 'Manual Delete Inventory'
        obj.save()
    return redirect('wms:layout')


@login_required
def col_update(request, pk):
    obj = get_object_or_404(Column, pk=pk)
    data = {}
    if request.method == 'POST':
        form = ColumnForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.save()
            data['form_is_valid'] = True
        else:
            data['form_is_valid'] = False
    else:
        form = ColumnForm(instance=obj)

    template_name = 'wms/layout/col_update.html'
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


@method_decorator(login_required, name='dispatch')
class ProductDatabaseView(SingleTableMixin, generic.TemplateView):
    template_name = 'wms/db_log/product_db.html'
    context_table_name = 'product_db'
    table_class = ProductDatabaseTable
    table_data = Product.objects.none()
    table_pagination = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'q': self.request.GET.get('q', '')
        })
        return context


@method_decorator(login_required, name='dispatch')
class ProductDatabaseJson(BaseDatatableView):
    model = Product

    def filter_queryset(self, qs):
        search = self.request.GET.get('search[value]', None)
        if search:
            conditions = ~Q(pk=None)
            qq = shlex.split(search)
            for q in qq:
                conditions &= Q(product_name__icontains=q) | Q(plant__plant_id__icontains=q)
            qs = qs.filter(conditions)
        return qs


@method_decorator(login_required, name='dispatch')
class StorageDatabaseView(SingleTableMixin, generic.TemplateView):
    template_name = 'wms/db_log/storage_db.html'
    context_table_name = 'storage_db'
    table_class = StorageDatabaseTable
    table_data = Storage.objects.none()
    table_pagination = False


@method_decorator(login_required, name='dispatch')
class StorageDatabaseJson(BaseDatatableView):
    def get_initial_queryset(self):
        pk = self.kwargs['pk']
        if pk in list(Product.objects.all().values_list('product_name', flat=True)):
            return Storage.objects.filter(have_inventory=True, inv_product__product_name=pk)
        elif pk in list(Plant.objects.all().values_list('plant_id', flat=True)):
            return Storage.objects.filter(have_inventory=True, inv_product__plant=pk)
        else:
            return Storage.objects.all()

    def filter_queryset(self, qs):
        search = self.request.GET.get('search[value]', None)
        if search:
            conditions = ~Q(pk=None)
            qq = shlex.split(search)
            for q in qq:
                conditions &= Q(storage_id__icontains=q) | Q(inv_product__product_name__icontains=q) | Q(lot_name__icontains=q)
            qs = qs.filter(conditions)
        return qs


@method_decorator(login_required, name='dispatch')
class ProductLogView(SingleTableMixin, generic.TemplateView):
    template_name = 'wms/db_log/product_log.html'
    context_table_name = 'product_log'
    table_class = ProductLogTable
    table_data = Product.history.none()
    table_pagination = False


@method_decorator(login_required, name='dispatch')
class ProductLogJson(BaseDatatableView):
    def get_initial_queryset(self):
        return Product.history.all()

    def render_column(self, row, column):
        if column in ['history_date']:
            return timezone.localtime(row.history_date).strftime('%a, %d %b %Y, %H:%M:%S')
        else:
            return super().render_column(row, column)


@method_decorator(login_required, name='dispatch')
class StorageLogView(SingleTableMixin, generic.TemplateView):
    template_name = 'wms/db_log/storage_log.html'
    context_table_name = 'storage_log'
    table_class = StorageLogTable
    table_data = Storage.history.none()
    table_pagination = False


@method_decorator(login_required, name='dispatch')
class StorageLogJson(BaseDatatableView):
    def get_initial_queryset(self):
        return Storage.history.all()

    def render_column(self, row, column):
        if column in ['history_date']:
            return timezone.localtime(row.history_date).strftime('%a, %d %b %Y, %H:%M:%S')
        else:
            return super().render_column(row, column)


@method_decorator(login_required, name='dispatch')
class AgvProductionPlanLogView(SingleTableMixin, generic.TemplateView):
    template_name = 'wms/db_log/plan_log.html'
    context_table_name = 'plan_log'
    table_class = AgvProductionPlanLogTable
    table_data = AgvProductionPlan.history.none()
    table_pagination = False


@method_decorator(login_required, name='dispatch')
class AgvProductionPlanLogJson(BaseDatatableView):
    def get_initial_queryset(self):
        return AgvProductionPlan.history.all()

    def render_column(self, row, column):
        if column in ['history_date']:
            return timezone.localtime(row.history_date).strftime('%a, %d %b %Y, %H:%M:%S')
        else:
            return super().render_column(row, column)


@method_decorator(login_required, name='dispatch')
class RobotQueueLogView(SingleTableMixin, generic.TemplateView):
    template_name = 'wms/db_log/robot_log.html'
    context_table_name = 'robot_log'
    table_class = RobotQueueLogTable
    table_data = RobotQueue.history.none()
    table_pagination = False


@method_decorator(login_required, name='dispatch')
class RobotQueueLogJson(BaseDatatableView):
    def get_initial_queryset(self):
        return RobotQueue.history.all()

    def render_column(self, row, column):
        if column in ['history_date']:
            return timezone.localtime(row.history_date).strftime('%a, %d %b %Y, %H:%M:%S')
        else:
            return super().render_column(row, column)


@method_decorator(login_required, name='dispatch')
class AgvQueueLogView(SingleTableMixin, generic.TemplateView):
    template_name = 'wms/db_log/queue_log.html'
    context_table_name = 'queue_log'
    table_class = AgvQueueLogTable
    table_data = AgvQueue.history.none()
    table_pagination = False


@method_decorator(login_required, name='dispatch')
class AgvQueueLogJson(BaseDatatableView):
    def get_initial_queryset(self):
        return AgvQueue.history.all()

    def render_column(self, row, column):
        if column in ['history_date', 'created_on']:
            return timezone.localtime(row.history_date).strftime('%a, %d %b %Y, %H:%M:%S')
        else:
            return super().render_column(row, column)


@method_decorator(login_required, name='dispatch')
class AgvTransferLogView(SingleTableMixin, generic.TemplateView):
    template_name = 'wms/db_log/transfer_log.html'
    context_table_name = 'transfer_log'
    table_class = AgvTransferLogTable
    table_data = AgvTransfer.history.none()
    table_pagination = False


@method_decorator(login_required, name='dispatch')
class AgvTransferLogJson(BaseDatatableView):
    def get_initial_queryset(self):
        pk = self.kwargs['pk']
        return AgvTransfer.history.filter(id=pk)

    def render_column(self, row, column):
        if column in ['history_date']:
            return timezone.localtime(row.history_date).strftime('%a, %d %b %Y, %H:%M:%S')
        else:
            return super().render_column(row, column)


@method_decorator([login_required, groups_required('Staff')], name='dispatch')
class AgvListView(generic.TemplateView):
    template_name = 'wms/agv.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'storage_form' not in context:
            context['storage_form'] = StorageOrderForm()
        if 'retrieval_form' not in context:
            context['retrieval_form'] = RetrievalOrderForm()
        if 'move_form' not in context:
            context['move_form'] = MoveOrderForm()
        context.update({
            'plan_db': AgvProductionPlan.objects.all(),
            'robot_db': RobotQueue.objects.all(),
            'queue_db': AgvQueue.objects.all(),
            'transfer_db': AgvTransfer.objects.all()
        })

        return context

    def post(self, request, *args, **kwargs):
        context = {}
        if 'storage' in request.POST:
            form = StorageOrderForm(request.POST)
            if form.is_valid():
                obj = AgvProductionPlan(product_name=Product.objects.get(product_name=request.POST.get('product_name_storage', None)))
                obj.qty_total = obj.qty_remain = request.POST.get('qty_bag', None)
                obj.lot_name = request.POST.get('lot_name', None)
                obj.changeReason = 'New Production Plan'
                obj.save()
                return redirect(request.META.get('HTTP_REFERER'))
            else:
                context['storage_form'] = form
        if 'retrieval' in request.POST:
            form = RetrievalOrderForm(request.POST)
            if form.is_valid():
                retrieve_list = request.POST.get('retrieve_list', None).split(',')
                buffer_list = request.POST.get('buffer_list', None).split(',')
                for i in range(len(retrieve_list)):
                    obj_from = get_object_or_404(Storage, storage_id=retrieve_list[i])
                    obj_to = get_object_or_404(Storage, storage_id=buffer_list[i])
                    obj = AgvQueue()
                    obj.product_name = obj_from.inv_product
                    obj.lot_name = obj_from.lot_name
                    obj.qty_act = obj_from.inv_qty
                    obj.created_on = obj_from.created_on
                    obj.robot_no = None
                    obj.pick_id = obj_from
                    obj.place_id = obj_to
                    obj.mode = 2
                    obj.updated = 0
                    obj.changeReason = 'Retrieve Order'
                    obj.save()
                return redirect(request.META.get('HTTP_REFERER'))
            else:
                context['retrieval_form'] = form
        if 'move' in request.POST:
            form = MoveOrderForm(request.POST)
            if form.is_valid():
                obj_from = get_object_or_404(Storage, storage_id=request.POST.get('move_from', None))
                obj_to = get_object_or_404(Storage, storage_id=request.POST.get('move_to', None))
                obj = AgvQueue()
                obj.product_name = obj_from.inv_product
                obj.lot_name = obj_from.lot_name
                obj.qty_act = obj_from.inv_qty
                obj.created_on = obj_from.created_on
                obj.robot_no = None
                obj.pick_id = obj_from
                obj.place_id = obj_to
                obj.mode = 2
                obj.updated = 0
                obj.changeReason = 'Move Order'
                obj.save()
                return redirect(request.META.get('HTTP_REFERER'))
            else:
                context['move_form'] = form

        return render(request, self.template_name, self.get_context_data(**context))


@login_required
def get_data_storage_form(request):
    data = {}
    if request.method == 'POST':
        obj = get_object_or_404(Product, product_name=request.POST.get('product_name_storage', None))
        data['qty_storage'] = obj.qty_storage
        data['qty_storage_avail'] = obj.qty_storage_avail
        data['qty_limit'] = obj.qty_limit
    return JsonResponse(data)


@login_required
def get_data_retrieval_form(request):
    data = {}
    if request.method == 'POST':
        obj = get_object_or_404(Product.objects.select_related('plant'), product_name=request.POST.get('product_name_retrieve', None))

        # Calculate inventory qty, exclude in queue #
        qs_inventory = Storage.objects.filter(inv_product=obj.product_name, storage_for=obj.product_name).exclude(storage_id__in=AgvQueue.objects.filter(mode=2).values('pick_id'))
        inv_bag = qs_inventory.aggregate(models.Sum('inv_qty'))['inv_qty__sum']
        data['inv_bag'] = inv_bag if inv_bag else 0

        # Calculate available inventory qty #
        # Only retrieve from pre-assigned column and don't have misplace or new(less than 7 days) inventory before it #
        qs_avail_inventory = qs_inventory
        condition_misplace = ~Q(inv_product=obj.product_name) & Q(storage_for=obj.product_name) & Q(have_inventory=True)
        condition_age = Q(have_inventory=True) & Q(created_on__gte=timezone.now() - timezone.timedelta(days=7))
        qs_exclude = Storage.objects.filter(condition_misplace | condition_age)
        for column_id in qs_exclude.order_by().distinct().values_list('column_id', flat=True):
            exclude_outer = qs_exclude.filter(column_id=column_id).order_by('row').last()
            if exclude_outer:
                qs_avail_inventory = qs_avail_inventory.exclude(column_id=column_id, row__lte=exclude_outer.row)
        avail_inv_bag = qs_avail_inventory.aggregate(models.Sum('inv_qty'))['inv_qty__sum']
        data['avail_inv_bag'] = avail_inv_bag if avail_inv_bag else 0

        avail_inventory_zone_a = qs_avail_inventory.filter(zone='A').order_by('area', 'col', '-row')
        avail_inventory_zone_b = qs_avail_inventory.filter(zone='B').order_by('-area', '-col', '-row')
        pk_avail_inventory_list = list(avail_inventory_zone_a.values_list('storage_id', flat=True)) + list(avail_inventory_zone_b.values_list('storage_id', flat=True))
        if pk_avail_inventory_list:
            # Find oldest inventory column
            column_zone_a = Storage.objects.filter(inv_product=obj.product_name, storage_for=obj.product_name, zone='A').order_by('area', 'col')
            column_zone_b = Storage.objects.filter(inv_product=obj.product_name, storage_for=obj.product_name, zone='B').order_by('-area', '-col')
            column_id_list = list(column_zone_a.distinct().values_list('column_id', flat=True)) + list(column_zone_b.distinct().values_list('column_id', flat=True))
            df_created_on = pd.DataFrame(columns=['column_id', 'created_on']).set_index('column_id')
            for column_id in column_id_list:
                qs_oldest_inventory_in_column = Storage.objects.filter(column_id=column_id, have_inventory=True)
                if qs_oldest_inventory_in_column.exists():
                    oldest_inventory_in_column = qs_oldest_inventory_in_column.order_by('-row')[0]
                    df_created_on.loc[column_id] = [oldest_inventory_in_column.created_on]
            if len(df_created_on) > 0:
                pk_avail_inventory_list_sort = []
                column_id_list = list(df_created_on.sort_values(by=['created_on'], ascending=True).index)
                for column_id in column_id_list:
                    if Storage.objects.filter(storage_id__in=pk_avail_inventory_list, column_id=column_id).exists():
                        storage_id_list = list(Storage.objects.filter(storage_id__in=pk_avail_inventory_list, column_id=column_id).order_by('-row').values_list('storage_id', flat=True))
                        pk_avail_inventory_list_sort += storage_id_list
                pk_avail_inventory_list = pk_avail_inventory_list_sort

        # Calculate buffer qty #
        # Only store to pre-assigned buffer and don't have any inventory before it #
        qs_avail_buffer = Storage.objects.filter(column_id__for_buffer__buffer_for_plant__plant_id=obj.plant.plant_id)
        qs_occupied = qs_avail_buffer.filter(Q(have_inventory=True) | Q(storage_id__in=AgvQueue.objects.all().values('place_id')))
        for column_id in qs_occupied.order_by().distinct().values_list('column_id', flat=True):
            occupied_outer = qs_occupied.filter(column_id=column_id).order_by('row').last()
            if occupied_outer:
                qs_avail_buffer = qs_avail_buffer.exclude(column_id=column_id, row__lte=occupied_outer.row)

        avail_buffer_zone_a = qs_avail_buffer.filter(zone='A').order_by('area', 'col', 'row')
        avail_buffer_zone_b = qs_avail_buffer.filter(zone='B').order_by('-area', '-col', 'row')
        pk_avail_buffer_list = list(avail_buffer_zone_a.values_list('storage_id', flat=True)) + list(avail_buffer_zone_b.values_list('storage_id', flat=True))
        if pk_avail_buffer_list:
            # Find last buffer column
            column_zone_a = Storage.objects.filter(column_id__for_buffer__buffer_for_plant__plant_id=obj.plant.plant_id, zone='A').order_by('area', 'col')
            column_zone_b = Storage.objects.filter(column_id__for_buffer__buffer_for_plant__plant_id=obj.plant.plant_id, zone='B').order_by('-area', '-col')
            column_id_list = list(column_zone_a.distinct().values_list('column_id', flat=True)) + list(column_zone_b.distinct().values_list('column_id', flat=True))
            df_updated_on = pd.DataFrame(columns=['column_id', 'updated_on']).set_index('column_id')
            for column_id in column_id_list:
                qs_last_inventory_in_column = Storage.objects.filter(column_id=column_id, have_inventory=True)
                if qs_last_inventory_in_column.exists():
                    last_inventory_in_column = qs_last_inventory_in_column.order_by('-row')[0]
                    df_updated_on.loc[column_id] = [last_inventory_in_column.created_on]
            if len(df_updated_on) > 0:
                last_column_id = list(df_updated_on.sort_values(by=['updated_on'], ascending=False).index)[0]
                last_column_id_index = column_id_list.index(last_column_id)
                column_id_list = column_id_list[last_column_id_index:] + column_id_list[:last_column_id_index]
                for column_id in column_id_list:
                    if Storage.objects.filter(storage_id__in=pk_avail_buffer_list, column_id=column_id).exists():
                        first_storage_id = Storage.objects.filter(storage_id__in=pk_avail_buffer_list, column_id=column_id).order_by('row').first().storage_id
                        first_storage_id_index = pk_avail_buffer_list.index(first_storage_id)
                        break
                    # Find next available column for obj_to if last buffer column is full
                pk_avail_buffer_list = pk_avail_buffer_list[first_storage_id_index:] + pk_avail_buffer_list[:first_storage_id_index]

        data['buffer_space'] = len(pk_avail_buffer_list)
        data['buffer_list'] = pk_avail_buffer_list

        # Calculate retrieve qty #
        if request.POST.get('qty_bag', None) == '':
            data['qty_act_bag'] = 0
            data['qty_act_pallet'] = 0
        else:
            qty_bag = int(request.POST.get('qty_bag', None))
            qty_act_bag = 0
            pk_retrieve_list = []
            for pk in pk_avail_inventory_list:
                if qty_bag <= 0:
                    break
                else:
                    inv_qty = get_object_or_404(qs_avail_inventory, storage_id=pk).inv_qty
                    qty_bag = qty_bag - inv_qty
                    qty_act_bag = qty_act_bag + inv_qty
                    pk_retrieve_list.append(pk)
            data['qty_act_bag'] = qty_act_bag
            data['qty_act_pallet'] = len(pk_retrieve_list)
            data['retrieve_list'] = pk_retrieve_list

    return JsonResponse(data)


@login_required
def get_data_move_form(request):
    data = {}
    if request.method == 'POST':
        if Storage.objects.select_related('inv_product').filter(storage_id=request.POST.get('move_from', None)).exists():
            obj_from = get_object_or_404(Storage.objects.select_related('inv_product'), storage_id=request.POST.get('move_from', None))
            data['product_name_move'] = obj_from.inv_product.product_name if obj_from.inv_product else None
            data['qty_bag'] = obj_from.inv_qty
            data['lot_name'] = obj_from.lot_name
            obj_to = get_object_or_404(Storage, storage_id=request.POST.get('move_to', None))
            data['storage_for'] = obj_to.storage_for
    return JsonResponse(data)


@login_required
def get_data_agv_position(request):
    data = {}
    if request.method == 'GET':
        obj_transfer = get_object_or_404(AgvTransfer, id=1)
        agv_x, agv_y, agv_beta = transfer_adjust(obj_transfer)
        agv_col, agv_row = position_cal(agv_x, agv_y)
        data['agv_col'] = agv_col
        data['agv_row'] = agv_row
        data['agv_beta'] = int(agv_beta)
        obj_robot1 = get_object_or_404(RobotStatus, robot_no=1)
        obj_robot2 = get_object_or_404(RobotStatus, robot_no=2)
        data['robot_qty1'] = int(obj_robot1.qty_act) if obj_robot1.qty_act else 0
        data['robot_qty2'] = int(obj_robot2.qty_act) if obj_robot2.qty_act else 0
    return JsonResponse(data)


class AutoCloseView(generic.TemplateView):
    template_name = 'wms/auto_close.html'


@method_decorator(login_required, name='dispatch')
class PlanFormView(generic.TemplateView):
    template_name = 'wms/agv/plan_form.html'


@login_required
def plan_update(request, pk):
    obj = get_object_or_404(AgvProductionPlan, pk=pk)
    data = {}
    if request.method == 'POST':
        form = AgvProductionPlanForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.changeReason = 'Manual Update Production Plan'
            obj.save()
            data['form_is_valid'] = True
        else:
            data['form_is_valid'] = False
    else:
        form = AgvProductionPlanForm(instance=obj)

    template_name = 'wms/agv/plan_update.html'
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


@login_required
def plan_delete(request, pk):
    obj = get_object_or_404(AgvProductionPlan, pk=pk)
    obj.changeReason = 'Manual Delete Production Plan'
    obj.delete()
    return redirect('wms:auto_close')


@login_required
def plan_clear(request):
    qs = AgvProductionPlan.objects.all()
    for obj in qs:
        obj.changeReason = 'Manual Delete Production Plan'
        obj.delete()
    return redirect(request.META.get('HTTP_REFERER'))


@method_decorator(login_required, name='dispatch')
class QueueFormView(generic.TemplateView):
    template_name = 'wms/agv/queue_form.html'


@login_required
def queue_update(request, pk):
    obj = get_object_or_404(AgvQueue, pk=pk)
    data = {}
    if request.method == 'POST':
        form = AgvQueueForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            if obj.mode == 1:
                obj_to = get_object_or_404(Storage, storage_id=obj.place_id)
                obj.place_id = obj_to
                obj.mode = 1
                obj.updated = 0
            elif obj.mode == 2:
                obj_from = get_object_or_404(Storage, storage_id=obj.pick_id)
                obj_to = get_object_or_404(Storage, storage_id=obj.place_id)
                obj.product_name = obj_from.inv_product
                obj.lot_name = obj_from.lot_name
                obj.qty_act = obj_from.inv_qty
                obj.created_on = obj_from.created_on
                obj.pick_id = obj_from
                obj.place_id = obj_to
                obj.mode = 2
                obj.updated = 0
            obj.changeReason = 'Manual Update AGV Queue'
            obj.save()
            data['form_is_valid'] = True
        else:
            data['form_is_valid'] = False
    else:
        form = AgvQueueForm(instance=obj)

    template_name = 'wms/agv/queue_update.html'
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


@login_required
def queue_delete(request, pk):
    obj = get_object_or_404(AgvQueue, pk=pk)
    obj.changeReason = 'Manual Delete AGV Queue'
    obj.delete()
    return redirect('wms:auto_close')


@login_required
def queue_clear(request):
    qs = AgvQueue.objects.all()
    for obj in qs:
        obj.changeReason = 'Manual Delete AGV Queue'
        obj.delete()
    return redirect(request.META.get('HTTP_REFERER'))


@method_decorator(login_required, name='dispatch')
class RobotFormView(generic.TemplateView):
    template_name = 'wms/agv/robot_form.html'


@login_required
def robot_update(request, pk):
    obj = get_object_or_404(RobotQueue, pk=pk)
    data = {}
    if request.method == 'POST':
        form = RobotQueueForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.changeReason = 'Manual Update Robot Queue'
            obj.save()
            data['form_is_valid'] = True
        else:
            data['form_is_valid'] = False
    else:
        form = RobotQueueForm(instance=obj)

    template_name = 'wms/agv/robot_update.html'
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


@login_required
def robot_delete(request, pk):
    obj = get_object_or_404(RobotQueue, pk=pk)
    obj.changeReason = 'Manual Delete Robot Queue'
    obj.delete()
    return redirect('wms:auto_close')


@login_required
def robot_clear(request):
    qs = RobotQueue.objects.all()
    for obj in qs:
        obj.changeReason = 'Manual Delete Robot Queue'
        obj.delete()
    return redirect(request.META.get('HTTP_REFERER'))


@method_decorator(login_required, name='dispatch')
class TransferFormView(generic.TemplateView):
    template_name = 'wms/agv/transfer_form.html'


@login_required
def transfer_update(request, pk):
    obj = get_object_or_404(AgvTransfer, pk=pk)
    data = {}
    if request.method == 'POST':
        form = AgvTransferForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.changeReason = 'Manual Update AGV Transfer'
            obj.save()
            data['form_is_valid'] = True
        else:
            data['form_is_valid'] = False
    else:
        form = AgvTransferForm(instance=obj)

    template_name = 'wms/agv/transfer_update.html'
    context = {'form': form, 'queue_db': AgvQueue.objects.all()}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


@method_decorator([login_required, groups_required('Staff')], name='dispatch')
class AgvTestListView(generic.TemplateView):
    template_name = 'wms/agv_debug.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'storage_form' not in context:
            context['storage_form'] = StorageOrderForm()
        if 'robot_form' not in context:
            context['robot_form'] = RobotQueueForm()
        if 'manualtransfer_form' not in context:
            context['manualtransfer_form'] = ManualTransferForm()
        context.update({
            'plan_db': AgvProductionPlan.objects.all(),
            'robot_db': RobotQueue.objects.all(),
            'queue_db': AgvQueue.objects.all(),
            'transfer_db': AgvTransfer.objects.all()
        })
        return context

    def post(self, request, *args, **kwargs):
        context = {}
        if 'storage' in request.POST:
            form = StorageOrderForm(request.POST)
            if form.is_valid():
                obj = AgvProductionPlan(product_name=Product.objects.get(product_name=request.POST.get('product_name', None)))
                obj.qty_total = obj.qty_remain = request.POST.get('qty_bag', None)
                obj.lot_name = request.POST.get('lot_name', None)
                obj.changeReason = 'New Production Plan'
                obj.save()
                return redirect(request.META.get('HTTP_REFERER'))
            else:
                context['storage_form'] = form
        if 'robot' in request.POST:
            form = RobotQueueForm(request.POST)
            if form.is_valid():
                obj = RobotQueue()
                obj.robot_no = request.POST.get('robot_no', None)
                obj.product_name = request.POST.get('product_name', None)
                obj.qty_act = request.POST.get('qty_act', None)
                obj.updated = request.POST.get('updated', None)
                obj.changeReason = 'Manual Create Robot Queue'
                obj.save()
                return redirect(request.META.get('HTTP_REFERER'))
            else:
                context['robot_form'] = form
        if 'manualtransfer' in request.POST:
            form = ManualTransferForm(request.POST)
            if form.is_valid():
                agv_no = 1
                qs_transfer = AgvTransfer.objects.filter(id=agv_no)
                pattern = float(request.POST.get('pattern', None))
                robot_no = int(request.POST.get('robot_no_manual', None))
                obj_storage = get_object_or_404(Storage, storage_id=request.POST.get('place_id', None))
                runway_row = 9
                if pattern != 2.0:
                    target_col = obj_storage.layout_col
                    target_row = obj_storage.layout_row
                elif pattern == 2.0:
                    target_col = 45 if robot_no == 1 else 40
                    target_row = runway_row

                agv_route_manual(agv_no, qs_transfer, pattern, target_col, target_row)

                return redirect(request.META.get('HTTP_REFERER'))
            else:
                context['manualtransfer_form'] = form

        return render(request, self.template_name, self.get_context_data(**context))


@login_required
def agv_to_home(request, pk):
    agv_no = pk
    qs_transfer = AgvTransfer.objects.filter(id=agv_no)
    agv_route_home(agv_no, qs_transfer)

    return redirect(request.META.get('HTTP_REFERER'))


class GraphTrendView(generic.TemplateView):
    template_name = 'wms/graph_trend.html'

    def get_context_data(self, **kwargs):
        dt_stop = datetime.now()
        dt_start = dt_stop.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        form_data = {
            'label': 'all',
            'date_filter': '{} - {}'.format(dt_start.strftime('%d/%m/%y %H:%M'), dt_stop.strftime('%d/%m/%y %H:%M')),
            'data': 25,
        }

        if self.request.GET.get('label'):
            form_data['label'] = self.request.GET.get('label')
        if self.request.GET.get('date_filter'):
            date_filter = self.request.GET.get('date_filter').split(' - ')
            dt_start, dt_stop = [datetime.strptime(dt, '%d/%m/%y %H:%M') for dt in date_filter]
            form_data['date_filter'] = '{} - {}'.format(dt_start.strftime('%d/%m/%y %H:%M'), dt_stop.strftime('%d/%m/%y %H:%M'))
        if self.request.GET.get('data'):
            if self.request.GET.get('data') != '' and int(self.request.GET.get('data')) > 0:
                form_data['data'] = int(self.request.GET.get('data'))

        dt_list = pd.date_range(dt_start, dt_stop, periods=form_data['data']).to_list()
        dt_list = [timezone.make_aware(dt) for dt in dt_list]

        df_qty = pd.DataFrame(index=dt_list)

        if form_data['label'] == 'all':
            plant_list = list(Plant.objects.all().values_list('plant_id', flat=True))
            label_list = plant_list + [str(_('All'))]

            for plant in plant_list:
                product_list = list(get_object_or_404(Plant, plant_id=plant).product_set.all().values_list('product_name', flat=True))
                for product in product_list:
                    for dt in dt_list:
                        condition = Q(history_date__lte=dt, product_name=product)
                        df_qty.loc[dt, product] = Product.history.filter(condition).order_by('-history_date').first().qty_total if Product.history.filter(condition).exists() else 0
                df_qty[plant] = df_qty.loc[:, product_list].sum(axis=1)

            df_qty[str(_('All'))] = df_qty.loc[:, plant_list].sum(axis=1)

        else:
            plant = form_data['label']
            label_list = list(get_object_or_404(Plant, plant_id=plant).product_set.all().values_list('product_name', flat=True))
            product_list = label_list
            for product in product_list:
                for dt in dt_list:
                    condition = Q(history_date__lte=dt, product_name=product)
                    df_qty.loc[dt, product] = Product.history.filter(condition).order_by('-history_date').first().qty_total if Product.history.filter(condition).exists() else 0
                df_qty[product] = df_qty.loc[:, product_list].sum(axis=1)

        dt = [timezone.localtime(dt).strftime('%d/%m/%y %H:%M') for dt in dt_list]
        qty = {'{}'.format(label): df_qty[label].to_list() for label in label_list}

        context = super().get_context_data(**kwargs)
        context['form'] = GraphTrendForm(initial=form_data)
        context.update({
            'label_list': label_list,
            'dt': dt,
            'qty': qty,
        })
        return context
