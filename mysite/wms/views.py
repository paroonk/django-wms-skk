from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_list_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.views import generic
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
        in_stock_status = '{:,}'.format(
            Storage.objects.filter(have_inventory=True).aggregate(models.Sum('inv_qty'))['inv_qty__sum'] if Storage.objects.filter(have_inventory=True).aggregate(models.Sum('inv_qty'))['inv_qty__sum'] is not None else 0
        )
        in_stock_pct = '{:.0%}'.format(Storage.objects.filter(have_inventory=True).count() / Storage.objects.all().count() if Storage.objects.all() else 0)
        agv_run = AgvTransfer.objects.filter(run=1).count()
        agv_total = AgvTransfer.objects.all().count()

        # For Overview Graph
        overview_plant_list = list(enumerate([_('All')] + list(Product.objects.select_related('plant').order_by('plant_id').distinct().values_list('plant', flat=True))))

        # For Usage Graph
        qty_inventory_plant = []
        usage_plant_list = list(enumerate(list(Product.objects.order_by('plant_id').distinct().values_list('plant', flat=True))))
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

    col_range = range(1, 80)
    col_skips = {10, 14, 18}
    row_range = range(1, 22)
    row_skips = {}
    for col in (x for x in col_range if x not in col_skips):
        layout_col.append(col)
        layout[col] = {}
        for row in (y for y in row_range if y not in row_skips):
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
    for i in range(76):

        if i < 4 or i == 32 or i == 33:
            col_label = ''
            headers.append(col_label)
        elif i < 50:
            col_label = 'B{:02d}'.format(48 - i if i < 32 else 50 - i)
            headers.append(col_label)

        col_label = 'A{:02d}'.format(76 - i)
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
        context.update(
            {'layout': layout, 'headers': headers, 'footers': footers, 'layout_col': layout_col, 'zip_row': zip_row, 'in_queue': in_queue, 'agvtransfer': AgvTransfer.objects.all(),}
        )
        return context


######################################################################################################################################################
# @method_decorator(login_required, name='dispatch')
class LayoutDebugView(generic.TemplateView):
    template_name = 'wms/layout_debug.html'

    def get_context_data(self, **kwargs):
        obj_storage = Storage.objects.select_related('column_id', 'column_id__for_product', 'inv_product').all()
        layout, headers, footers, layout_col, zip_row = layout_map(obj_storage, debug=True)

        context = super().get_context_data(**kwargs)
        context.update(
            {'layout': layout, 'headers': headers, 'footers': footers, 'layout_col': layout_col, 'zip_row': zip_row,}
        )
        return context


######################################################################################################################################################
class LayoutAgeView(generic.TemplateView):
    template_name = 'wms/layout_age.html'

    def get_context_data(self, **kwargs):
        obj_storage = Storage.objects.select_related('column_id', 'column_id__for_product', 'inv_product').all()
        layout, headers, footers, layout_col, zip_row = layout_map(obj_storage, age=True)
        age_criteria = Setting.objects.get(id=1).age_criteria if Setting.objects.filter(id=1).exists() else 0

        context = super().get_context_data(**kwargs)
        context.update(
            {'layout': layout, 'headers': headers, 'footers': footers, 'layout_col': layout_col, 'zip_row': zip_row, 'age_criteria': age_criteria,}
        )
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
        context.update({'agvproductionplan': AgvProductionPlan.objects.all(), 'robotqueue': RobotQueue.objects.all(), 'agvqueue': AgvQueue.objects.all(), 'agvtransfer': AgvTransfer.objects.all()})

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
        context.update({'agvproductionplan': AgvProductionPlan.objects.all(), 'robotqueue': RobotQueue.objects.all(), 'agvqueue': AgvQueue.objects.all(), 'agvtransfer': AgvTransfer.objects.all()})
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
                obj.product_id = request.POST.get('product_id', None)
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
                target_col = int(request.POST.get('layout_col', None))
                target_row = int(request.POST.get('layout_row', None))
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
# @method_decorator(login_required, name='dispatch')
class HistoryGraphView(generic.TemplateView):
    template_name = 'wms/historygraph.html'

    def get_context_data(self, **kwargs):
        dt_stop = datetime.now()
        dt_start = dt_stop.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dt_format = '%d/%m/%y %H:%M'
        form_data = {
            'label': 'all',
            'date_filter': '{} - {}'.format(dt_start.strftime(dt_format), dt_stop.strftime(dt_format)),
            'data': 25,
        }

        form_data['label'] = self.request.GET.get('label')
        date_filter = self.request.GET.get('date_filter')
        if date_filter:
            dt_start, dt_stop = [datetime.strptime(dt, dt_format) for dt in date_filter.split(' - ')]
            form_data['date_filter'] = '{} - {}'.format(dt_start.strftime(dt_format), dt_stop.strftime(dt_format))
        data = self.request.GET.get('data')
        if data:
            form_data['data'] = int(data)

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
        context.update(
            {'instance': Storage, 'fields': zip(data, name, class_name),}
        )
        return context


######################################################################################################################################################
# @method_decorator(login_required, name='dispatch')
class ProductHistoryView(generic.TemplateView):
    template_name = 'wms/db_log/log_product.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = ['history_date', 'history_type', 'history_change_reason', 'product_name', 'qty_storage', 'qty_inventory', 'qty_buffer', 'qty_misplace', 'qty_total', 'qty_storage_avail', 'qty_inventory_avail']
        name = ['history_date', 'history_type', 'history_change_reason', 'product_name', 'qty_storage', 'qty_inventory', 'qty_buffer', 'qty_misplace', 'qty_total', 'qty_storage_avail', 'qty_inventory_avail']
        class_name = ['text-left', 'text-left', 'text-left', 'text-left', 'text-right', 'text-right', 'text-right', 'text-right', 'text-right', 'text-right', 'text-right']

        dt_stop = datetime.now()
        dt_start = dt_stop.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dt_format = '%d/%m/%y %H:%M'
        form_data = {
            'date_filter': '{} - {}'.format(dt_start.strftime(dt_format), dt_stop.strftime(dt_format)),
        }
        date_filter = self.request.GET.get('date_filter', None)
        if date_filter:
            dt_start, dt_stop = [datetime.strptime(dt, dt_format) for dt in date_filter.split(' - ')]
            form_data['date_filter'] = '{} - {}'.format(dt_start.strftime(dt_format), dt_stop.strftime(dt_format))

        context['form'] = LogFilterForm(initial=form_data)
        context.update(
            {'instance': Product.history.model, 'fields': zip(data, name, class_name),}
        )
        return context


# @method_decorator(login_required, name='dispatch')
class StorageHistoryView(generic.TemplateView):
    template_name = 'wms/db_log/log_storage.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = ['history_date', 'history_type', 'history_change_reason', 'storage_id', 'is_inventory', 'storage_for', 'have_inventory', 'inv_product', 'inv_qty']
        name = ['history_date', 'history_type', 'history_change_reason', 'storage_id', 'is_inventory', 'storage_for', 'have_inventory', 'inv_product.product_name', 'inv_qty']
        class_name = ['text-left', 'text-left', 'text-left', 'text-left', 'text-center', 'text-left', 'text-center', 'text-left', 'text-right']

        dt_stop = datetime.now()
        dt_start = dt_stop.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dt_format = '%d/%m/%y %H:%M'
        form_data = {
            'date_filter': '{} - {}'.format(dt_start.strftime(dt_format), dt_stop.strftime(dt_format)),
        }
        date_filter = self.request.GET.get('date_filter', None)
        if date_filter:
            dt_start, dt_stop = [datetime.strptime(dt, dt_format) for dt in date_filter.split(' - ')]
            form_data['date_filter'] = '{} - {}'.format(dt_start.strftime(dt_format), dt_stop.strftime(dt_format))

        context['form'] = LogFilterForm(initial=form_data)
        context.update(
            {'instance': Storage.history.model, 'fields': zip(data, name, class_name),}
        )
        return context


# @method_decorator(login_required, name='dispatch')
class AgvProductionPlanHistoryView(generic.TemplateView):
    template_name = 'wms/db_log/log_agvproductionplan.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = ['history_date', 'history_type', 'history_change_reason', 'id', 'product_name', 'qty_total', 'qty_remain', 'lot_name']
        name = ['history_date', 'history_type', 'history_change_reason', 'id', 'product_name.product_name', 'qty_total', 'qty_remain', 'lot_name']
        class_name = ['text-left', 'text-left', 'text-left', 'text-left', 'text-left', 'text-right', 'text-right', 'text-left']

        dt_stop = datetime.now()
        dt_start = dt_stop.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dt_format = '%d/%m/%y %H:%M'
        form_data = {
            'date_filter': '{} - {}'.format(dt_start.strftime(dt_format), dt_stop.strftime(dt_format)),
        }
        date_filter = self.request.GET.get('date_filter', None)
        if date_filter:
            dt_start, dt_stop = [datetime.strptime(dt, dt_format) for dt in date_filter.split(' - ')]
            form_data['date_filter'] = '{} - {}'.format(dt_start.strftime(dt_format), dt_stop.strftime(dt_format))

        context['form'] = LogFilterForm(initial=form_data)
        context.update(
            {'instance': AgvProductionPlan.history.model, 'fields': zip(data, name, class_name),}
        )
        return context


# @method_decorator(login_required, name='dispatch')
class RobotQueueHistoryView(generic.TemplateView):
    template_name = 'wms/db_log/log_robotqueue.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = ['history_date', 'history_type', 'history_change_reason', 'id', 'robot_no', 'product_id', 'qty_act']
        name = ['history_date', 'history_type', 'history_change_reason', 'id', 'robot_no', 'product_id', 'qty_act']
        class_name = ['text-left', 'text-left', 'text-left', 'text-left', 'text-left', 'text-left', 'text-right']

        dt_stop = datetime.now()
        dt_start = dt_stop.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dt_format = '%d/%m/%y %H:%M'
        form_data = {
            'date_filter': '{} - {}'.format(dt_start.strftime(dt_format), dt_stop.strftime(dt_format)),
        }
        date_filter = self.request.GET.get('date_filter', None)
        if date_filter:
            dt_start, dt_stop = [datetime.strptime(dt, dt_format) for dt in date_filter.split(' - ')]
            form_data['date_filter'] = '{} - {}'.format(dt_start.strftime(dt_format), dt_stop.strftime(dt_format))

        context['form'] = LogFilterForm(initial=form_data)
        context.update(
            {'instance': RobotQueue.history.model, 'fields': zip(data, name, class_name),}
        )
        return context


# @method_decorator(login_required, name='dispatch')
class AgvQueueHistoryView(generic.TemplateView):
    template_name = 'wms/db_log/log_agvqueue.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = ['history_date', 'history_type', 'history_change_reason', 'id', 'product_name', 'lot_name', 'qty_act', 'created_on', 'robot_no', 'pick_id', 'place_id', 'mode']
        name = ['history_date', 'history_type', 'history_change_reason', 'id', 'product_name.product_name', 'lot_name', 'qty_act', 'created_on', 'robot_no', 'pick_id.storage_id', 'place_id.storage_id', 'mode']
        class_name = ['text-left', 'text-left', 'text-left', 'text-left', 'text-left', 'text-left', 'text-right', 'text-left', 'text-left', 'text-left', 'text-left', 'text-center']

        dt_stop = datetime.now()
        dt_start = dt_stop.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dt_format = '%d/%m/%y %H:%M'
        form_data = {
            'date_filter': '{} - {}'.format(dt_start.strftime(dt_format), dt_stop.strftime(dt_format)),
        }
        date_filter = self.request.GET.get('date_filter', None)
        if date_filter:
            dt_start, dt_stop = [datetime.strptime(dt, dt_format) for dt in date_filter.split(' - ')]
            form_data['date_filter'] = '{} - {}'.format(dt_start.strftime(dt_format), dt_stop.strftime(dt_format))

        context['form'] = LogFilterForm(initial=form_data)
        context.update(
            {'instance': AgvQueue.history.model, 'fields': zip(data, name, class_name),}
        )
        return context


# @method_decorator(login_required, name='dispatch')
class AgvTransferHistoryView(generic.TemplateView):
    template_name = 'wms/db_log/log_agvtransfer.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = ['history_date', 'history_type', 'history_change_reason', 'id', 'run', 'status', 'step', 'pause', 'pattern']
        name = ['history_date', 'history_type', 'history_change_reason', 'id', 'run', 'status', 'step', 'pause', 'pattern']
        class_name = ['text-left', 'text-left', 'text-left', 'text-left', 'text-left', 'text-left', 'text-center', 'text-left', 'text-left']

        dt_stop = datetime.now()
        dt_start = dt_stop.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dt_format = '%d/%m/%y %H:%M'
        form_data = {
            'date_filter': '{} - {}'.format(dt_start.strftime(dt_format), dt_stop.strftime(dt_format)),
        }
        date_filter = self.request.GET.get('date_filter', None)
        if date_filter:
            dt_start, dt_stop = [datetime.strptime(dt, dt_format) for dt in date_filter.split(' - ')]
            form_data['date_filter'] = '{} - {}'.format(dt_start.strftime(dt_format), dt_stop.strftime(dt_format))

        context['form'] = LogFilterForm(initial=form_data)
        context.update(
            {'instance': AgvTransfer.history.model, 'fields': zip(data, name, class_name),}
        )
        return context


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
        type = self.kwargs['type']
        if type == 'all':
            queryset = self.queryset
        elif type in list(Product.objects.all().values_list('product_name', flat=True)):
            queryset = self.queryset.filter(have_inventory=True, inv_product__product_name=type)
        elif type in list(Plant.objects.all().values_list('plant_id', flat=True)):
            queryset = self.queryset.filter(have_inventory=True, inv_product__plant=type)
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


class StorageHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Storage.history.all()
    serializer_class = StorageHistorySerializer

    def get_queryset(self):
        queryset = self.queryset
        date_filter = self.request.query_params.get('date_filter', None)
        dt_format = '%d/%m/%y %H:%M'
        if date_filter:
            date_range = [timezone.make_aware(datetime.strptime(dt, dt_format)) for dt in date_filter.split(' - ')]
            queryset = queryset.filter(history_date__range=date_range)
        return queryset


class AgvProductionPlanHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AgvProductionPlan.history.all()
    serializer_class = AgvProductionPlanHistorySerializer

    def get_queryset(self):
        queryset = self.queryset
        date_filter = self.request.query_params.get('date_filter', None)
        dt_format = '%d/%m/%y %H:%M'
        if date_filter:
            date_range = [timezone.make_aware(datetime.strptime(dt, dt_format)) for dt in date_filter.split(' - ')]
            queryset = queryset.filter(history_date__range=date_range)
        return queryset


class RobotQueueHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RobotQueue.history.all()
    serializer_class = RobotQueueHistorySerializer

    def get_queryset(self):
        queryset = self.queryset
        date_filter = self.request.query_params.get('date_filter', None)
        dt_format = '%d/%m/%y %H:%M'
        if date_filter:
            date_range = [timezone.make_aware(datetime.strptime(dt, dt_format)) for dt in date_filter.split(' - ')]
            queryset = queryset.filter(history_date__range=date_range)
        return queryset


class AgvQueueHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AgvQueue.history.all()
    serializer_class = AgvQueueHistorySerializer

    def get_queryset(self):
        queryset = self.queryset
        date_filter = self.request.query_params.get('date_filter', None)
        dt_format = '%d/%m/%y %H:%M'
        if date_filter:
            date_range = [timezone.make_aware(datetime.strptime(dt, dt_format)) for dt in date_filter.split(' - ')]
            queryset = queryset.filter(history_date__range=date_range)
        return queryset


class AgvTransferHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AgvTransfer.history.all()
    serializer_class = AgvTransferHistorySerializer

    def get_queryset(self):
        id = self.kwargs['id']
        queryset = self.queryset.filter(id=id)

        date_filter = self.request.query_params.get('date_filter', None)
        dt_format = '%d/%m/%y %H:%M'
        if date_filter:
            date_range = [timezone.make_aware(datetime.strptime(dt, dt_format)) for dt in date_filter.split(' - ')]
            queryset = queryset.filter(history_date__range=date_range)
        return queryset


######################################################################################################################################################
class OverviewGraphViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()

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
        product_name = list(queryset.values_list('product_name', flat=True))
        product_color = list(queryset.values_list('bg_color', flat=True))
        qty_inventory = list(queryset.values_list('qty_inventory', flat=True))
        qty_buffer = list(queryset.values_list('qty_buffer', flat=True))
        qty_misplace = list(queryset.values_list('qty_misplace', flat=True))
        qty_storage = list(queryset.values_list('qty_storage', flat=True))
        qty_total = list(queryset.values_list('qty_total', flat=True))

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

        plant_list = list(Product.objects.order_by('plant_id').distinct().values_list('plant', flat=True))
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
            dt_stop = datetime.now()
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
            label_list = product_list
            for product in product_list:
                for dt in dt_list:
                    condition = Q(history_date__lte=dt, product_name=product)
                    df_qty.loc[dt, product] = Product.history.filter(condition).order_by('-history_date').first().qty_total if Product.history.filter(condition).exists() else 0
                df_qty[product] = df_qty.loc[:, product_list].sum(axis=1)

        dt = [timezone.localtime(dt).strftime(dt_format) for dt in dt_list]
        qty = {'{}'.format(product): df_qty[product].to_list() for product in label_list}

        data = {'label_list': label_list, 'dt': dt, 'qty': qty}
        return Response(data)
