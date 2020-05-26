from datetime import datetime
from itertools import chain

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_list_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django_pandas.io import read_frame
from drf_multiple_model.pagination import MultipleModelLimitOffsetPagination
from drf_multiple_model.views import ObjectMultipleModelAPIView
from rest_framework import viewsets
from rest_framework.response import Response

from .forms import *
from .serializers import *


######################################################################################################################################################
def permission_denied(request):
    messages.add_message(request, messages.INFO, "You don't have authorization to view this page. Please sign in with authorized user account.")
    return redirect(request.META.get('HTTP_REFERER'))


def groups_required(*groups):
    return user_passes_test(lambda u: u.groups.filter(name__in=groups).exists() | u.is_superuser, login_url='/permission_denied/', redirect_field_name=None)


def redirect_home(request):
    return redirect('wms:dashboard')


######################################################################################################################################################
class AutoCloseView(generic.TemplateView):
    template_name = 'wms/auto_close.html'


######################################################################################################################################################
class DashboardView(generic.TemplateView):
    template_name = 'wms/dashboard.html'

    def get_context_data(self, **kwargs):
        in_stock = Storage.objects.filter(have_inventory=True).aggregate(models.Sum('inv_qty'))['inv_qty__sum']
        in_stock_status = '{:}'.format(in_stock if in_stock is not None else 0)
        in_stock_pct = '{:.0%}'.format(Storage.objects.filter(have_inventory=True).count() / Storage.objects.all().count() if Storage.objects.all() else 0)
        agv_run = AgvTransfer.objects.filter(run=1, pause=0).count()
        agv_total = AgvTransfer.objects.all().count()
        robot_qty_1 = RobotStatus.objects.get(robot_no=1).qty_act if RobotStatus.objects.filter(robot_no=1).exists() else 'N/A'
        robot_qty_2 = RobotStatus.objects.get(robot_no=2).qty_act if RobotStatus.objects.filter(robot_no=2).exists() else 'N/A'

        plant_list = list(Product.objects.select_related('plant').exclude(plant__plant_id__isnull=True).order_by('plant_id').distinct().values_list('plant', flat=True))

        # For Overview Graph
        overview_plant_list = list(enumerate([_('All')] + plant_list))

        # For Usage Graph
        qty_inventory_plant = []
        usage_plant_list = list(enumerate(plant_list))
        for i, plant in usage_plant_list:
            qty_inventory_plant.append(Storage.objects.filter(column_id__is_inventory=True, column_id__for_product__plant__plant_id=plant).aggregate(models.Sum('inv_qty'))['inv_qty__sum'])
            if qty_inventory_plant[-1] == None:
                qty_inventory_plant[-1] = 0

        context = super().get_context_data(**kwargs)
        context.update(
            {
                'in_stock_status': in_stock_status,
                'in_stock_pct': in_stock_pct,
                'agv_run': agv_run,
                'agv_total': agv_total,
                'robot_qty_1': robot_qty_1,
                'robot_qty_2': robot_qty_2,
                # For Overview Graph
                'overview_plant_list': overview_plant_list,
                # For Usage Graph
                'usage_plant_list': usage_plant_list,
                'qty_inventory_plant': qty_inventory_plant,
            }
        )
        return context


######################################################################################################################################################
def layout_map(obj_storage, debug=False, age=False):
    layout = {}
    layout_col = []
    layout_row = []

    col_range = range(1, 77)
    row_range = range(1, 22)
    for col in col_range:
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
        elif debug and s.is_inventory and s.column_id.storage_for:
            layout[s.layout_col][s.layout_row]['bg_color'] = df_product.loc[s.column_id.storage_for, 'bg_color']
            layout[s.layout_col][s.layout_row]['font_color'] = df_product.loc[s.column_id.storage_for, 'font_color']

    headers = []
    footers = []
    for i in range(1, 77):

        if i in [1, 2, 3, 4, 33, 34]:
            col_label = ''
            headers.append(col_label)
        elif i < 49:
            col_label = 'B{:02d}'.format(47 - i if i < 33 else 49 - i)
            headers.append(col_label)

        col_label = 'A{:02d}'.format(77 - i)
        footers.append(col_label)

    index = ['R{:02d}'.format(i + 1) for i in range(7)] + 3 * [''] + ['R{:02d}'.format(11 - i) for i in range(11)]
    zip_row = zip(index, layout_row)

    return layout, headers, footers, layout_col, zip_row


######################################################################################################################################################
# @method_decorator(login_required, name='dispatch')
class LayoutView(generic.TemplateView):
    template_name = 'wms/layout.html'

    def get_context_data(self, **kwargs):
        obj_storage = Storage.objects.select_related('column_id', 'column_id__for_product', 'inv_product').all()
        layout, headers, footers, layout_col, zip_row = layout_map(obj_storage)
        in_queue = list(set(AgvQueue.objects.all().values_list('pick_id', flat=True)) | set(AgvQueue.objects.all().values_list('place_id', flat=True)))
        context = super().get_context_data(**kwargs)
        context.update({'layout': layout, 'headers': headers, 'footers': footers, 'layout_col': layout_col, 'zip_row': zip_row, 'in_queue': in_queue})
        return context


######################################################################################################################################################
# @method_decorator(login_required, name='dispatch')
class LayoutDebugView(generic.TemplateView):
    template_name = 'wms/layout_debug.html'

    def get_context_data(self, **kwargs):
        obj_storage = Storage.objects.select_related('column_id', 'column_id__for_product', 'inv_product').all()
        layout, headers, footers, layout_col, zip_row = layout_map(obj_storage, debug=True)

        context = super().get_context_data(**kwargs)
        context.update({'layout': layout, 'headers': headers, 'footers': footers, 'layout_col': layout_col, 'zip_row': zip_row})
        return context


######################################################################################################################################################
class LayoutAgeView(generic.TemplateView):
    template_name = 'wms/layout_age.html'

    def get_context_data(self, **kwargs):
        obj_storage = Storage.objects.select_related('column_id', 'column_id__for_product', 'inv_product').all()
        layout, headers, footers, layout_col, zip_row = layout_map(obj_storage, age=True)
        age_criteria = Setting.objects.get(id=1).age_criteria if Setting.objects.filter(id=1).exists() else 0

        context = super().get_context_data(**kwargs)
        context.update({'layout': layout, 'headers': headers, 'footers': footers, 'layout_col': layout_col, 'zip_row': zip_row, 'age_criteria': age_criteria})
        return context


######################################################################################################################################################
# @login_required
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
        obj.created_on = timezone.localtime().strftime('%d/%m/%Y %H:%M:%S')
        form = InventoryForm(instance=obj)

    template_name = 'wms/layout/inv_create.html'
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


# @login_required
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
        obj.created_on = timezone.localtime(obj.created_on).strftime('%d/%m/%Y %H:%M:%S')
        form = InventoryForm(instance=obj)

    template_name = 'wms/layout/inv_update.html'
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


# @login_required
def inv_delete(request, pk):
    obj = get_object_or_404(Storage, pk=pk)
    obj.inv_product = None
    obj.inv_qty = None
    obj.lot_name = None
    obj.created_on = None
    obj.updated_on = timezone.now()
    obj.changeReason = 'Manual Delete Inventory'
    obj.save()
    return redirect(request.META.get('HTTP_REFERER'))


######################################################################################################################################################
# @login_required
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
            obj.created_on = timezone.localtime(obj.created_on).strftime('%d/%m/%Y %H:%M:%S')
        else:
            obj = qs_storage.first()
            if obj.column_id.is_inventory:
                obj.inv_product = obj.column_id.for_product
                obj.inv_qty = obj.inv_product.qty_limit if obj.inv_product else 0
            obj.created_on = timezone.localtime().strftime('%d/%m/%Y %H:%M:%S')

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


# @login_required
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
    return redirect(request.META.get('HTTP_REFERER'))


######################################################################################################################################################
# @login_required
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


######################################################################################################################################################
# @method_decorator([login_required, groups_required('Staff')], name='dispatch')
class AgvView(generic.TemplateView):
    template_name = 'wms/agv.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'storage_form' not in context:
            context['storage_form'] = StorageOrderForm()
        if 'retrieval_form' not in context:
            context['retrieval_form'] = RetrievalOrderForm()
        if 'move_form' not in context:
            context['move_form'] = MoveOrderForm()

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


######################################################################################################################################################
# @method_decorator([login_required, groups_required('Staff')], name='dispatch')
class AgvTestView(generic.TemplateView):
    template_name = 'wms/agv_debug.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'storage_form' not in context:
            context['storage_form'] = StorageOrderForm()
        if 'robot_form' not in context:
            context['robot_form'] = RobotQueueForm()
        if 'manualtransfer_form' not in context:
            context['manualtransfer_form'] = ManualTransferForm()
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
                obj.product_id = RobotTag.objects.get(product_id=request.POST.get('product_id', None))
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
                agv_no = int(request.POST.get('agv_no', None))
                qs_transfer = AgvTransfer.objects.filter(id=agv_no)
                pattern = float(request.POST.get('pattern', None))
                target_col = float(request.POST.get('layout_col', None))
                target_row = float(request.POST.get('layout_row', None))
                agv_route_manual(agv_no, qs_transfer, pattern, target_col, target_row)

                return redirect(request.META.get('HTTP_REFERER'))
            else:
                context['manualtransfer_form'] = form

        return render(request, self.template_name, self.get_context_data(**context))


######################################################################################################################################################
# @login_required
def get_data_storage_form(request):
    data = {}
    if request.method == 'GET':
        obj = get_object_or_404(Product, product_name=request.GET.get('product_name_storage', None))
        data['qty_storage'] = obj.qty_storage
        data['qty_storage_avail'] = obj.qty_storage_avail
        data['qty_limit'] = obj.qty_limit
    return JsonResponse(data)


# @login_required
def get_data_retrieval_form(request):
    data = {}
    if request.method == 'GET':
        obj = get_object_or_404(Product.objects.select_related('plant'), product_name=request.GET.get('product_name_retrieve', None))

        # Calculate inventory qty, exclude in queue
        qs_inventory = Storage.objects.filter(inv_product=obj.product_name, storage_for=obj.product_name).exclude(storage_id__in=AgvQueue.objects.filter(mode=2).values('pick_id'))
        inv_bag = qs_inventory.aggregate(models.Sum('inv_qty'))['inv_qty__sum']
        data['inv_bag'] = inv_bag if inv_bag else 0

        # Calculate available inventory qty
        # Only retrieve from pre-assigned column and don't have misplace or new(less than 7 days) inventory before it
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

        pk_avail_inventory_list = list(qs_avail_inventory.order_by('col', '-row').values_list('storage_id', flat=True))
        if pk_avail_inventory_list:
            # Find oldest inventory column
            column_id_list = list(Storage.objects.filter(inv_product=obj.product_name, storage_for=obj.product_name).order_by('col').distinct().values_list('column_id', flat=True))
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

        # Calculate buffer qty
        # Only store to pre-assigned buffer and don't have any inventory before it
        qs_avail_buffer = Storage.objects.filter(column_id__for_buffer__buffer_for_plant__plant_id=obj.plant.plant_id)
        qs_occupied = qs_avail_buffer.filter(Q(have_inventory=True) | Q(storage_id__in=AgvQueue.objects.all().values('place_id')))
        for column_id in qs_occupied.order_by().distinct().values_list('column_id', flat=True):
            occupied_outer = qs_occupied.filter(column_id=column_id).order_by('row').last()
            if occupied_outer:
                qs_avail_buffer = qs_avail_buffer.exclude(column_id=column_id, row__lte=occupied_outer.row)

        pk_avail_buffer_list = list(qs_avail_buffer.order_by('col', 'row').values_list('storage_id', flat=True))
        if pk_avail_buffer_list:
            # Find last buffer column
            column_id_list = list(Storage.objects.filter(column_id__for_buffer__buffer_for_plant__plant_id=obj.plant.plant_id).order_by('col').distinct().values_list('column_id', flat=True))
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

        # Calculate retrieve qty
        if request.GET.get('qty_bag', None) == '':
            data['qty_act_bag'] = 0
            data['qty_act_pallet'] = 0
        else:
            qty_bag = int(request.GET.get('qty_bag', None))
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


# @login_required
def get_data_move_form(request):
    data = {}
    if request.method == 'GET':
        if Storage.objects.select_related('inv_product').filter(storage_id=request.GET.get('move_from', None)).exists():
            obj_from = get_object_or_404(Storage.objects.select_related('inv_product'), storage_id=request.GET.get('move_from', None))
            data['product_name_move'] = obj_from.inv_product.product_name if obj_from.inv_product else None
            data['qty_bag'] = obj_from.inv_qty
            data['lot_name'] = obj_from.lot_name
            obj_to = get_object_or_404(Storage, storage_id=request.GET.get('move_to', None))
            data['storage_for'] = obj_to.storage_for
    return JsonResponse(data)


######################################################################################################################################################
class ServerLogView(generic.TemplateView):
    template_name = 'wms/serverlog.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        with open('serverlog.txt', 'r') as file_object:
            log = file_object.read()
            context['log'] = log
        return context


######################################################################################################################################################
# @method_decorator(login_required, name='dispatch')
class HistoryGraphView(generic.TemplateView):
    template_name = 'wms/historygraph.html'

    def get_context_data(self, **kwargs):
        dt_stop = timezone.localtime()
        dt_start = dt_stop.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dt_format = '%d/%m/%y %H:%M'

        label = self.request.GET.get('label', 'all')
        date_filter = self.request.GET.get('date_filter', '{} - {}'.format(dt_start.strftime(dt_format), dt_stop.strftime(dt_format)))
        data = int(self.request.GET.get('data', 25))

        form_data = {
            'label': label,
            'date_filter': date_filter,
            'data': data,
        }

        context = super().get_context_data(**kwargs)
        context['form'] = HistoryGraphForm(initial=form_data)
        return context


######################################################################################################################################################
# @method_decorator(login_required, name='dispatch')
class ProductView(generic.TemplateView):
    template_name = 'wms/db_log/db_product.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = ['product_name', 'plant', 'qty_limit', 'qty_storage', 'qty_inventory', 'qty_buffer', 'qty_misplace', 'qty_total', 'qty_storage_avail', 'qty_inventory_avail']
        name = ['product_name', 'plant.plant_id', 'qty_limit', 'qty_storage', 'qty_inventory', 'qty_buffer', 'qty_misplace', 'qty_total', 'qty_storage_avail', 'qty_inventory_avail']
        class_name = ['text-left', 'text-left', 'text-center', 'text-right', 'text-right', 'text-right', 'text-right', 'text-right', 'text-right', 'text-right', 'text-right']
        context.update({'instance': Product, 'fields': zip(data, name, class_name), 'q': self.request.GET.get('q', '')})
        return context


# @method_decorator(login_required, name='dispatch')
class StorageView(generic.TemplateView):
    template_name = 'wms/db_log/db_storage.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = ['storage_id', 'is_inventory', 'storage_for', 'have_inventory', 'inv_product', 'inv_qty', 'lot_name', 'created_on', 'updated_on']
        name = ['storage_id', 'is_inventory', 'storage_for', 'have_inventory', 'inv_product.product_name', 'inv_qty', 'lot_name', 'created_on', 'updated_on']
        class_name = ['text-left', 'text-center', 'text-left', 'text-center', 'text-left', 'text-left', 'text-right', 'text-left', 'text-left', 'text-left']
        context.update({'instance': Storage, 'fields': zip(data, name, class_name)})
        return context


######################################################################################################################################################
# @method_decorator(login_required, name='dispatch')
class ProductHistoryView(generic.TemplateView):
    template_name = 'wms/db_log/log_product.html'
    data = ['history_date', 'history_type', 'history_change_reason', 'product_name', 'qty_storage', 'qty_inventory', 'qty_buffer', 'qty_misplace', 'qty_total', 'qty_storage_avail', 'qty_inventory_avail']
    name = ['history_date', 'history_type', 'history_change_reason', 'product_name', 'qty_storage', 'qty_inventory', 'qty_buffer', 'qty_misplace', 'qty_total', 'qty_storage_avail', 'qty_inventory_avail']
    class_name = ['text-left', 'text-left', 'text-left', 'text-left', 'text-right', 'text-right', 'text-right', 'text-right', 'text-right', 'text-right', 'text-right']
    instance = Product.history.model

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = self.data
        name = self.name
        class_name = self.class_name
        instance = self.instance

        dt_stop = timezone.localtime()
        dt_start = dt_stop.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dt_format = '%d/%m/%y %H:%M'
        date_filter = self.request.GET.get('date_filter', '{} - {}'.format(dt_start.strftime(dt_format), dt_stop.strftime(dt_format)))

        form_data = {
            'date_filter': date_filter,
        }

        context['form'] = LogFilterForm(initial=form_data)
        context.update({'instance': instance, 'fields': zip(data, name, class_name)})
        return context


# @method_decorator(login_required, name='dispatch')
class StorageHistoryView(ProductHistoryView):
    template_name = 'wms/db_log/log_storage.html'
    data = ['history_date', 'history_type', 'history_change_reason', 'storage_id', 'is_inventory', 'storage_for', 'have_inventory', 'inv_product', 'inv_qty']
    name = ['history_date', 'history_type', 'history_change_reason', 'storage_id', 'is_inventory', 'storage_for', 'have_inventory', 'inv_product.product_name', 'inv_qty']
    class_name = ['text-left', 'text-left', 'text-left', 'text-left', 'text-center', 'text-left', 'text-center', 'text-left', 'text-right']
    instance = Storage.history.model


# @method_decorator(login_required, name='dispatch')
class AgvProductionPlanHistoryView(ProductHistoryView):
    template_name = 'wms/db_log/log_agvproductionplan.html'
    data = ['history_date', 'history_type', 'history_change_reason', 'id', 'product_name', 'qty_total', 'qty_remain', 'lot_name']
    name = ['history_date', 'history_type', 'history_change_reason', 'id', 'product_name.product_name', 'qty_total', 'qty_remain', 'lot_name']
    class_name = ['text-left', 'text-left', 'text-left', 'text-left', 'text-left', 'text-right', 'text-right', 'text-left']
    instance = AgvProductionPlan.history.model


# @method_decorator(login_required, name='dispatch')
class RobotQueueHistoryView(ProductHistoryView):
    template_name = 'wms/db_log/log_robotqueue.html'
    data = ['history_date', 'history_type', 'history_change_reason', 'id', 'robot_no', 'product_id', 'qty_act']
    name = ['history_date', 'history_type', 'history_change_reason', 'id', 'robot_no', 'product_id', 'qty_act']
    class_name = ['text-left', 'text-left', 'text-left', 'text-left', 'text-left', 'text-left', 'text-right']
    instance = RobotQueue.history.model


# @method_decorator(login_required, name='dispatch')
class AgvQueueHistoryView(ProductHistoryView):
    template_name = 'wms/db_log/log_agvqueue.html'
    data = ['history_date', 'history_type', 'history_change_reason', 'id', 'product_name', 'lot_name', 'qty_act', 'created_on', 'robot_no', 'pick_id', 'place_id', 'mode']
    name = ['history_date', 'history_type', 'history_change_reason', 'id', 'product_name.product_name', 'lot_name', 'qty_act', 'created_on', 'robot_no', 'pick_id.storage_id', 'place_id.storage_id', 'mode']
    class_name = ['text-left', 'text-left', 'text-left', 'text-left', 'text-left', 'text-left', 'text-right', 'text-left', 'text-left', 'text-left', 'text-left', 'text-center']
    instance = AgvQueue.history.model


# @method_decorator(login_required, name='dispatch')
class AgvTransferHistoryView(ProductHistoryView):
    template_name = 'wms/db_log/log_agvtransfer.html'
    data = ['history_date', 'history_type', 'history_change_reason', 'id', 'run', 'status', 'step', 'pause', 'pattern']
    name = ['history_date', 'history_type', 'history_change_reason', 'id', 'run', 'status', 'step', 'pause', 'pattern']
    class_name = ['text-left', 'text-left', 'text-left', 'text-left', 'text-left', 'text-left', 'text-center', 'text-left', 'text-left']
    instance = AgvTransfer.history.model


######################################################################################################################################################
# FormView for edit data
# @method_decorator(login_required, name='dispatch')
class AgvProductionPlanView(generic.TemplateView):
    template_name = 'wms/agv/agvproductionplan_form.html'


# @method_decorator(login_required, name='dispatch')
class AgvQueueView(generic.TemplateView):
    template_name = 'wms/agv/agvqueue_form.html'


# @method_decorator(login_required, name='dispatch')
class RobotQueueView(generic.TemplateView):
    template_name = 'wms/agv/robotqueue_form.html'


# @method_decorator(login_required, name='dispatch')
class AgvTransferView(generic.TemplateView):
    template_name = 'wms/agv/agvtransfer_form.html'


######################################################################################################################################################
# Function for CRUD data
# @login_required
def agvproductionplan_update(request, pk):
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

    template_name = 'wms/agv/agvproductionplan_update.html'
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


# @login_required
def agvproductionplan_delete(request, pk):
    obj = get_object_or_404(AgvProductionPlan, pk=pk)
    obj.changeReason = 'Manual Delete Production Plan'
    obj.delete()
    return redirect('wms:auto_close')


# @login_required
def agvproductionplan_clear(request):
    qs = AgvProductionPlan.objects.all()
    for obj in qs:
        obj.changeReason = 'Manual Delete Production Plan'
        obj.delete()
    return redirect(request.META.get('HTTP_REFERER'))


######################################################################################################################################################
# @login_required
def agvqueue_update(request, pk):
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

    template_name = 'wms/agv/agvqueue_update.html'
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


# @login_required
def agvqueue_delete(request, pk):
    obj = get_object_or_404(AgvQueue, pk=pk)
    obj.changeReason = 'Manual Delete AGV Queue'
    obj.delete()
    return redirect('wms:auto_close')


# @login_required
def agvqueue_clear(request):
    qs = AgvQueue.objects.all()
    for obj in qs:
        obj.changeReason = 'Manual Delete AGV Queue'
        obj.delete()
    return redirect(request.META.get('HTTP_REFERER'))


######################################################################################################################################################
# @login_required
def robotqueue_update(request, pk):
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

    template_name = 'wms/agv/robotqueue_update.html'
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


# @login_required
def robotqueue_delete(request, pk):
    obj = get_object_or_404(RobotQueue, pk=pk)
    obj.changeReason = 'Manual Delete Robot Queue'
    obj.delete()
    return redirect('wms:auto_close')


# @login_required
def robotqueue_clear(request):
    qs = RobotQueue.objects.all()
    for obj in qs:
        obj.changeReason = 'Manual Delete Robot Queue'
        obj.delete()
    return redirect(request.META.get('HTTP_REFERER'))


######################################################################################################################################################
# @login_required
def agvtransfer_update(request, pk):
    obj = get_object_or_404(AgvTransfer, pk=pk)
    data = {}
    if request.method == 'POST':
        form = AgvTransferForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            agv_col = request.POST.get('agv_col', None)
            agv_row = request.POST.get('agv_row', None)
            obj_coor = get_object_or_404(Coordinate, layout_col=agv_col, layout_row=agv_row)
            obj.x_nav = obj_coor.coor_x
            obj.y_nav = obj_coor.coor_y
            obj.changeReason = 'Manual Update AGV Transfer'
            obj.save()
            data['form_is_valid'] = True
        else:
            data['form_is_valid'] = False
    else:
        form = AgvTransferForm(instance=obj)

    template_name = 'wms/agv/agvtransfer_update.html'
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


######################################################################################################################################################
# Agv to home
# @login_required
def agv_to_home(request, pk):
    agv_no = pk
    qs_transfer = AgvTransfer.objects.filter(id=agv_no)
    agv_route_home(agv_no, qs_transfer)

    return redirect(request.META.get('HTTP_REFERER'))


######################################################################################################################################################
# API for data
class AgvRobotStatusViewSet(viewsets.ViewSetMixin, ObjectMultipleModelAPIView):
    querylist = [
        {'queryset': AgvTransfer.objects.all(), 'serializer_class': AgvStatusSerializer, 'label': 'agv_status'},
        {'queryset': RobotStatus.objects.all(), 'serializer_class': RobotStatusSerializer, 'label': 'robot_status'},
    ]
    pagination_class = MultipleModelLimitOffsetPagination


class AgvTransferViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AgvTransfer.objects.all()
    serializer_class = AgvTransferSerializer


class AgvProductionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AgvProductionPlan.objects.all()
    serializer_class = AgvProductionPlanSerializer


class RobotQueueViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RobotQueue.objects.all()
    serializer_class = RobotQueueSerializer


class AgvQueueViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AgvQueue.objects.all()
    serializer_class = AgvQueueSerializer


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class StorageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Storage.objects.all()
    serializer_class = StorageSerializer

    def get_queryset(self):
        _type = self.kwargs['type']
        if _type == 'all':
            queryset = self.queryset
        elif _type in list(Product.objects.all().values_list('product_name', flat=True)):
            queryset = self.queryset.filter(have_inventory=True, inv_product__product_name=_type)
        elif _type in list(Plant.objects.all().values_list('plant_id', flat=True)):
            queryset = self.queryset.filter(have_inventory=True, inv_product__plant=_type)
        else:
            queryset = self.queryset.none()
        return queryset


######################################################################################################################################################
class ProductHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.history.all()
    serializer_class = ProductHistorySerializer

    def get_queryset(self):
        queryset = self.queryset
        date_filter = self.request.query_params.get('date_filter', None)
        dt_format = '%d/%m/%y %H:%M'
        if date_filter:
            date_range = [timezone.make_aware(datetime.strptime(dt, dt_format)) for dt in date_filter.split(' - ')]
            queryset = queryset.filter(history_date__range=date_range)
        return queryset


class StorageHistoryViewSet(ProductHistoryViewSet):
    queryset = Storage.history.all()
    serializer_class = StorageHistorySerializer


class AgvProductionPlanHistoryViewSet(ProductHistoryViewSet):
    queryset = AgvProductionPlan.history.all()
    serializer_class = AgvProductionPlanHistorySerializer


class RobotQueueHistoryViewSet(ProductHistoryViewSet):
    queryset = RobotQueue.history.all()
    serializer_class = RobotQueueHistorySerializer


class AgvQueueHistoryViewSet(ProductHistoryViewSet):
    queryset = AgvQueue.history.all()
    serializer_class = AgvQueueHistorySerializer


class AgvTransferHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AgvTransfer.history.all()
    serializer_class = AgvTransferHistorySerializer

    def get_queryset(self):
        _id = self.kwargs['id']
        queryset = self.queryset.filter(id=_id)

        date_filter = self.request.query_params.get('date_filter', None)
        dt_format = '%d/%m/%y %H:%M'
        if date_filter:
            date_range = [timezone.make_aware(datetime.strptime(dt, dt_format)) for dt in date_filter.split(' - ')]
            queryset = queryset.filter(history_date__range=date_range)
        return queryset


######################################################################################################################################################
class OverviewGraphViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.select_related('plant').exclude(plant__plant_id__isnull=True)

    def get_queryset(self):
        queryset = self.queryset
        plant_id = self.request.query_params.get('plant_id', _('All'))
        if plant_id != _('All'):
            queryset = queryset.filter(plant__plant_id=plant_id)
        return queryset

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        plant_id = self.request.query_params.get('plant_id', _('All'))
        value_type = int(self.request.query_params.get('value_type', 0))

        df_product = read_frame(queryset, verbose=False)
        product_name = df_product['product_name'].tolist()
        product_color = df_product['bg_color'].tolist()
        qty_inventory = df_product['qty_inventory'].tolist()
        qty_buffer = df_product['qty_buffer'].tolist()
        qty_misplace = df_product['qty_misplace'].tolist()
        qty_storage = df_product['qty_storage'].tolist()
        qty_total = df_product['qty_total'].tolist()

        if value_type == 0:
            qty_inventory = qty_inventory
            qty_buffer = qty_buffer
            qty_misplace = qty_misplace
            qty_avail_storage = [storage - total for storage, total in zip(qty_storage, qty_total)]
        else:
            qty_inventory = [round(inventory / storage * 100, 2) for inventory, storage in zip(qty_inventory, qty_storage)]
            qty_buffer = [round(buffer / storage * 100, 2) for buffer, storage in zip(qty_buffer, qty_storage)]
            qty_misplace = [round(misplace / storage * 100, 2) for misplace, storage in zip(qty_misplace, qty_storage)]
            qty_avail_storage = [round((storage - total) / storage * 100, 2) for storage, total in zip(qty_storage, qty_total)]
        data = {
            'plant_id': plant_id,
            'value_type': value_type,
            'product_name': product_name,
            'product_color': product_color,
            'qty_inventory': [{'value': inventory, 'itemStyle': {'color': color}} for inventory, color in zip(qty_inventory, product_color)],
            'qty_buffer': qty_buffer,
            'qty_misplace': qty_misplace,
            'qty_avail_storage': qty_avail_storage,
        }
        return Response(data)


######################################################################################################################################################
class UsageGraphViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Storage.objects.all()

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())

        plant_list = list(Product.objects.select_related('plant').exclude(plant__plant_id__isnull=True).order_by('plant_id').distinct().values_list('plant', flat=True))
        qty_inventory = [queryset.filter(column_id__is_inventory=True, column_id__for_product__plant__plant_id=plant).aggregate(models.Sum('inv_qty'))['inv_qty__sum'] for plant in plant_list]

        data = {
            'qty_inventory': [{'name': plant, 'value': inventory if inventory else 0} for plant, inventory in zip(plant_list, qty_inventory)],
        }
        return Response(data)


######################################################################################################################################################
class HistoryGraphViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.history.all()

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())

        dt_format = '%d/%m/%y %H:%M'
        label = self.request.query_params.get('label', 'all')
        date_filter = self.request.query_params.get('date_filter', None)
        data = int(self.request.query_params.get('data', 25))

        if date_filter:
            dt_start, dt_stop = [datetime.strptime(dt, dt_format) for dt in date_filter.split(' - ')]
        else:
            dt_stop = timezone.localtime()
            dt_start = dt_stop.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dt_list = pd.date_range(dt_start, dt_stop, periods=data).to_list()
        dt_list = [timezone.make_aware(dt) for dt in dt_list]

        df_qty = pd.DataFrame(index=dt_list)
        if label == 'all':
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
            plant = label
            product_list = list(get_object_or_404(Plant, plant_id=plant).product_set.all().values_list('product_name', flat=True))
            label_list = product_list + [plant]
            for product in product_list:
                for dt in dt_list:
                    condition = Q(history_date__lte=dt, product_name=product)
                    df_qty.loc[dt, product] = Product.history.filter(condition).order_by('-history_date').first().qty_total if Product.history.filter(condition).exists() else 0
            df_qty[plant] = df_qty.sum(axis=1)

        dt = [timezone.localtime(dt).strftime(dt_format) for dt in dt_list]
        qty = {'{}'.format(product): df_qty[product].to_list() for product in label_list}

        data = {'label_list': label_list, 'dt': dt, 'qty': qty}
        return Response(data)


######################################################################################################################################################
class ReportStockDataView(generic.TemplateView):
    template_name = 'wms/report/report_stockdata.html'

    def get_context_data(self, **kwargs):
        by = self.request.GET.get('by', 'product')
        month = int(self.request.GET.get('month', timezone.localtime().month))
        year = int(self.request.GET.get('year', timezone.localtime().year))

        form_data = {
            'by': by,
            'month': month,
            'year': year,
        }

        data = ['plant', 'qty_storage', 'qty_total', 'qty_produce', 'qty_sale']
        name = [_('Plant'), _('Storage Qty'), _('Ending Stock'), _('Production/Month'), _('Sales/Month')]

        if by == 'product':
            data = ['product_name'] + data
            name = [_('Product Name')] + name
            class_name = ['text-left'] * 2 + ['text-right'] * 4
            width = [20] * 6
        else:
            class_name = ['text-left'] + ['text-right'] * 4
            width = [20] * 5

        context = super().get_context_data(**kwargs)
        context['form'] = ReportStockDataForm(initial=form_data)
        context.update({'fields': zip(data, name, class_name, width)})
        return context


class ReportStockDataViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Report.objects.none()
    serializer_class = ReportSerializer

    def list(self, request):
        queryset = self.get_queryset()

        by = self.request.query_params.get('by', 'product')
        month = int(self.request.query_params.get('month', timezone.localtime().month))
        year = int(self.request.query_params.get('year', str(timezone.localtime().year)).replace(',', ''))

        if by == 'product':
            label_list = list(Product.objects.all().values_list('product_name', flat=True))
        else:
            label_list = list(Plant.objects.all().values_list('plant_id', flat=True))
        
        data = []
        for label in label_list:
            if by == 'product':
                qs_product = Product.objects.filter(product_name=label)
                plant = qs_product.first().plant.plant_id if qs_product.filter(plant__isnull=False).exists() else ''
                qty_storage = qs_product.aggregate(models.Sum('qty_storage'))['qty_storage__sum']
                qty_total = qs_product.aggregate(models.Sum('qty_total'))['qty_total__sum']
                
                qs_report = Report.objects.filter(year=year, month=month, product__product_name=label)
                qty_produce = qs_report.aggregate(models.Sum('qty_produce'))['qty_produce__sum'] if qs_report.exists() else 0
                qty_sale = qs_report.aggregate(models.Sum('qty_sale'))['qty_sale__sum'] if qs_report.exists() else 0
            else:
                qs_product = get_object_or_404(Plant, plant_id=label).product_set.all()
                qty_storage = qs_product.aggregate(models.Sum('qty_storage'))['qty_storage__sum']
                qty_total = qs_product.aggregate(models.Sum('qty_total'))['qty_total__sum']

                qs_report = Report.objects.filter(year=year, month=month, product__plant__plant_id=label)
                qty_produce = qs_report.aggregate(models.Sum('qty_produce'))['qty_produce__sum'] if qs_report.exists() else 0
                qty_sale = qs_report.aggregate(models.Sum('qty_sale'))['qty_sale__sum'] if qs_report.exists() else 0

            table_data = {'product_name': label, 'plant': plant} if by == 'product' else {'plant': label}
            table_data.update({
                'qty_storage': qty_storage,
                'qty_total': qty_total,
                'qty_produce': qty_produce,
                'qty_sale': qty_sale,
            })
            data.append(table_data)

        return Response(data)


######################################################################################################################################################
class ReportMonthlyProduceView(generic.TemplateView):
    template_name = 'wms/report/report_m_produce.html'

    def get_context_data(self, **kwargs):
        plant = self.request.GET.get('plant', 'all')
        year = int(self.request.GET.get('year', str(timezone.localtime().year)).replace(',', ''))

        form_data = {
            'plant': plant,
            'year': year,
        }

        if plant == 'all':
            label_list = [plant.replace('.', ',') for plant in list(Plant.objects.all().values_list('plant_id', flat=True))]
        else:
            label_list = [product.replace('.', ',') for product in list(get_object_or_404(Plant, plant_id=plant).product_set.all().values_list('product_name', flat=True))]

        data = ['month'] + label_list + ['sum']
        name = [_('Month')] + label_list + [_('Sum')]
        class_name = ['text-left'] + ['text-right'] * (len(label_list) + 1)
        width = [5] + [math.floor(95 / (len(label_list) + 1))] * (len(label_list) + 1)

        context = super().get_context_data(**kwargs)
        context['form'] = ReportMonthlyForm(initial=form_data)
        context.update({
            'fields': zip(data, name, class_name, width),
            'label_list': label_list
        })
        return context


class ReportMonthlySaleView(ReportMonthlyProduceView):
    template_name = 'wms/report/report_m_sale.html'


class ReportMonthlyProduceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Report.objects.none()
    serializer_class = ReportSerializer
    mode = 'produce'

    def list(self, request):
        queryset = self.get_queryset()
        mode = self.mode

        plant = self.request.query_params.get('plant', 'all')
        year = int(self.request.query_params.get('year', str(timezone.localtime().year)).replace(',', ''))

        if plant == 'all':
            label_list = list(Plant.objects.all().values_list('plant_id', flat=True))
        else:
            label_list = list(get_object_or_404(Plant, plant_id=plant).product_set.all().values_list('product_name', flat=True))

        data = []
        for month in range(1, 13):
            table_data = {'month': '{} {}'.format(calendar.month_abbr[month], str(year))}
            if plant == 'all':
                for plant_id in label_list:
                    name = plant_id.replace('.', ',')
                    qs_report = Report.objects.filter(year=year, month=month, product__plant__plant_id=plant_id)
                    value = qs_report.aggregate(models.Sum('qty_{}'.format(mode)))['qty_{}__sum'.format(mode)] if qs_report.exists() else 0
                    table_data.update({name: value})
            else:
                for product_name in label_list:
                    name = product_name.replace('.', ',')
                    qs_report = Report.objects.filter(year=year, month=month, product__product_name=product_name)
                    value = qs_report.aggregate(models.Sum('qty_{}'.format(mode)))['qty_{}__sum'.format(mode)] if qs_report.exists() else 0
                    table_data.update({name: value})

            table_data.update({'sum': sum([table_data[label] for label in label_list])})
            data.append(table_data)

        return Response(data)


class ReportMonthlySaleViewSet(ReportMonthlyProduceViewSet):
    queryset = Report.objects.none()
    serializer_class = ReportSerializer
    mode = 'sale'


######################################################################################################################################################
class ReportDailyProduceView(generic.TemplateView):
    template_name = 'wms/report/report_d_produce.html'

    def get_context_data(self, **kwargs):
        plant = self.request.GET.get('plant', 'all')
        month = int(self.request.GET.get('month', timezone.localtime().month))
        year = int(self.request.GET.get('year', timezone.localtime().year))

        form_data = {
            'plant': plant,
            'month': month,
            'year': year,
        }

        if plant == 'all':
            label_list = [plant.replace('.', ',') for plant in list(Plant.objects.all().values_list('plant_id', flat=True))]
        else:
            label_list = [product.replace('.', ',') for product in list(get_object_or_404(Plant, plant_id=plant).product_set.all().values_list('product_name', flat=True))]

        data = ['day'] + label_list + ['sum']
        name = [_('Date')] + label_list + [_('Sum')]
        class_name = ['text-left'] + ['text-right'] * (len(label_list) + 1)
        width = [5] + [math.floor(95 / (len(label_list) + 1))] * (len(label_list) + 1)

        context = super().get_context_data(**kwargs)
        context['form'] = ReportDailyForm(initial=form_data)
        context.update({
            'fields': zip(data, name, class_name, width),
            'label_list': label_list
        })
        return context


class ReportDailySaleView(ReportDailyProduceView):
    template_name = 'wms/report/report_d_sale.html'


class ReportDailyProduceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Report.objects.none()
    serializer_class = ReportSerializer
    mode = 'produce'

    def list(self, request):
        queryset = self.get_queryset()
        mode = self.mode

        plant = self.request.query_params.get('plant', 'all')
        month = int(self.request.query_params.get('month', timezone.localtime().month))
        year = int(self.request.query_params.get('year', str(timezone.localtime().year)).replace(',', ''))

        if plant == 'all':
            label_list = list(Plant.objects.all().values_list('plant_id', flat=True))
        else:
            label_list = list(get_object_or_404(Plant, plant_id=plant).product_set.all().values_list('product_name', flat=True))

        data = []
        for day in range(1, calendar.monthrange(year, month)[1] + 1):
            table_data = {'day': '{:02d}/{:02d}/{}'.format(day, month, str(year)[-2:])}
            if plant == 'all':
                for plant_id in label_list:
                    name = plant_id.replace('.', ',')
                    qs_report = Report.objects.filter(year=year, month=month, day=day, product__plant__plant_id=plant_id)
                    value = qs_report.aggregate(models.Sum('qty_{}'.format(mode)))['qty_{}__sum'.format(mode)] if qs_report.exists() else 0
                    table_data.update({name: value})
            else:
                for product_name in label_list:
                    name = product_name.replace('.', ',')
                    qs_report = Report.objects.filter(year=year, month=month, day=day, product__product_name=product_name)
                    value = qs_report.aggregate(models.Sum('qty_{}'.format(mode)))['qty_{}__sum'.format(mode)] if qs_report.exists() else 0
                    table_data.update({name: value})
            table_data.update({'sum': sum([table_data[label] for label in label_list])})
            data.append(table_data)

        return Response(data)


class ReportDailySaleViewSet(ReportDailyProduceViewSet):
    queryset = Report.objects.none()
    serializer_class = ReportSerializer
    mode = 'sale'
