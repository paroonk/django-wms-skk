from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_list_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin
from django_tables2.export.views import ExportMixin

from .forms import *
from .sched import transfer_adjust, position_cal, route_calculate
from .tables import *


def permission_denied(request):
    messages.add_message(request, messages.INFO, "You don't have authorization to view this page. Please sign in with authorized user account.")
    return redirect(request.META.get('HTTP_REFERER'))


def groups_required(*groups):
    return user_passes_test(lambda u: u.groups.filter(name__in=groups).exists() | u.is_superuser, login_url='/permission_denied/', redirect_field_name=None)


def redirect_home(request):
    return redirect('wms_skk:dashboard')


class DashboardView(generic.TemplateView):
    template_name = 'wms_skk/dashboard.html'

    obj = Product.objects.order_by().distinct().values_list('plant__plant_id', flat=True)

    def get_context_data(self, **kwargs):
        production_target = '{:,}'.format(1200000)
        current_production = '{:,}'.format(550000)
        in_stock_pct = '{:.0%}'.format(Storage.objects.filter(have_inventory=True).count() / Storage.objects.all().count() if Storage.objects.all() else 0)

        # For Overview Graph #
        overview_plant_list = list(enumerate(['All'] + list(Product.objects.select_related('plant').order_by().distinct().values_list('plant', flat=True))))
        product_id = {}
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
            if plant != 'All':
                product_id[i] = list(Product.objects.select_related('plant').filter(plant__plant_id=plant).values_list('product_id', flat=True))
                obj_list = get_list_or_404(Product, product_id__in=product_id[i])
            elif plant == 'All':
                product_id[i] = list(Product.objects.select_related('plant').all().values_list('product_id', flat=True))
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

        context = super(DashboardView, self).get_context_data(**kwargs)
        context.update({
            'production_target': production_target,
            'current_production': current_production,
            'in_stock_pct': in_stock_pct,
            # For Overview Graph #
            'overview_plant_list': overview_plant_list,
            'product_id': product_id,
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


@method_decorator(login_required, name='dispatch')
class LayoutView(generic.TemplateView):
    template_name = 'wms_skk/layout.html'

    def get_context_data(self, **kwargs):
        layout = {}
        layout_col = []
        layout_row = []

        skips = {40, 45}
        for col in (x for x in range(31, 97) if x not in skips):
            layout_col.append(col)
            layout[col] = {}
            for row in range(1, 21):
                if col == layout_col[0]:
                    layout_row.append(row)
                layout[col][row] = {}

        for col in layout_col:
            for row in layout_row:
                layout[col][row]['storage_id'] = ''
                layout[col][row]['is_inventory'] = ''
                layout[col][row]['storage_for'] = ''
        obj_storage = Storage.objects.select_related('column_id', 'column_id__for_product', 'inv_product').all()
        for s in obj_storage:
            layout[s.layout_col][s.layout_row]['storage_id'] = s.storage_id
            layout[s.layout_col][s.layout_row]['is_inventory'] = s.column_id.is_inventory
            layout[s.layout_col][s.layout_row]['storage_for'] = s.column_id.storage_for
            layout[s.layout_col][s.layout_row]['have_inventory'] = s.have_inventory
            if s.column_id.is_inventory and not s.have_inventory:
                try:
                    layout[s.layout_col][s.layout_row]['storage_for_name'] = s.column_id.for_product.name_th
                except AttributeError:
                    layout[s.layout_col][s.layout_row]['storage_for_name'] = 'No Data'
            if s.have_inventory:
                layout[s.layout_col][s.layout_row]['inv_product_name'] = s.inv_product.name_th if s.inv_product else 'No Data'
                layout[s.layout_col][s.layout_row]['inv_product'] = s.inv_product.product_id if s.inv_product else 'No Data'
                layout[s.layout_col][s.layout_row]['inv_qty'] = s.inv_qty
                layout[s.layout_col][s.layout_row]['lot_name'] = s.lot_name
                layout[s.layout_col][s.layout_row]['created_on'] = s.created_on
                layout[s.layout_col][s.layout_row]['updated_on'] = s.updated_on
                layout[s.layout_col][s.layout_row]['bg_color'] = s.bg_color
                layout[s.layout_col][s.layout_row]['font_color'] = s.font_color

        index = ['R{00}'.format(i + 1) for i in range(8)] + [''] + ['R{00}'.format(11 - i) for i in range(11)]

        in_queue = list(set(AgvQueue1.objects.all().values_list('pick_id', flat=True)) | set(AgvQueue1.objects.all().values_list('place_id', flat=True)))
        transfer1_db = AgvTransfer1.objects.all()

        context = super(LayoutView, self).get_context_data(**kwargs)
        context.update({
            'layout': layout,
            'header_1': ['B{00}'.format(11 - i) for i in range(11)],
            'header_2': ['C{00}'.format(4 - divmod(i, 4)[1]) for i in range(44)],
            'footer_1': ['A{00}'.format(16 - i) for i in range(16)],
            'footer_2': ['C{00}'.format(4 - divmod(i, 4)[1]) for i in range(64)],
            'layout_col': layout_col,
            'zip_row': zip(index, layout_row),
            'in_queue': in_queue,
            'transfer1_db': transfer1_db,
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
            obj.created_on = timezone.now()
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
        form = InventoryForm(instance=obj)

    template_name = 'wms_skk/layout/inv_create.html'
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

    template_name = 'wms_skk/layout/inv_update.html'
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
    return redirect('wms_skk:layout')


@method_decorator(login_required, name='dispatch')
class ProductDatabaseView(ExportMixin, SingleTableMixin, FilterView):
    template_name = 'wms_skk/product_db.html'
    context_table_name = 'product_db'
    table_class = ProductDatabaseTable
    table_pagination = {
        "per_page": 15
    }
    filterset_class = ProductDatabaseFilter


@method_decorator(login_required, name='dispatch')
class StorageDatabaseView(ExportMixin, SingleTableMixin, FilterView):
    template_name = 'wms_skk/storage_db.html'
    context_table_name = 'storage_db'
    table_class = StorageDatabaseTable
    table_pagination = {
        "per_page": 15
    }
    filterset_class = StorageDatabaseFilter


@method_decorator(login_required, name='dispatch')
class ProductLogView(generic.TemplateView):
    template_name = 'wms_skk/product_log.html'

    def get_context_data(self, **kwargs):
        context = super(ProductLogView, self).get_context_data(**kwargs)
        table = ProductLogTable(Product.history.all())
        table.paginate(page=self.request.GET.get("page", 1), per_page=15)
        context['product_log'] = table
        return context


@method_decorator(login_required, name='dispatch')
class StorageLogView(generic.TemplateView):
    template_name = 'wms_skk/storage_log.html'

    def get_context_data(self, **kwargs):
        context = super(StorageLogView, self).get_context_data(**kwargs)
        table = StorageLogTable(Storage.history.all())
        table.paginate(page=self.request.GET.get("page", 1), per_page=15)
        context['storage_log'] = table
        return context


@method_decorator(login_required, name='dispatch')
class AgvProductionPlanLogView(generic.TemplateView):
    template_name = 'wms_skk/plan_log.html'

    def get_context_data(self, **kwargs):
        context = super(AgvProductionPlanLogView, self).get_context_data(**kwargs)
        table = AgvProductionPlanLogTable(AgvProductionPlan.history.all())
        table.paginate(page=self.request.GET.get("page", 1), per_page=15)
        context['plan_log'] = table
        return context


@method_decorator(login_required, name='dispatch')
class RobotQueueLogView(generic.TemplateView):
    template_name = 'wms_skk/robot_log.html'

    def get_context_data(self, **kwargs):
        context = super(RobotQueueLogView, self).get_context_data(**kwargs)
        table = RobotQueueLogTable(RobotQueue.history.all())
        table.paginate(page=self.request.GET.get("page", 1), per_page=15)
        context['robot_log'] = table
        return context


@method_decorator(login_required, name='dispatch')
class AgvQueue1LogView(generic.TemplateView):
    template_name = 'wms_skk/queue1_log.html'

    def get_context_data(self, **kwargs):
        context = super(AgvQueue1LogView, self).get_context_data(**kwargs)
        table = AgvQueue1LogTable(AgvQueue1.history.all())
        table.paginate(page=self.request.GET.get("page", 1), per_page=15)
        context['queue1_log'] = table
        return context


@method_decorator(login_required, name='dispatch')
class AgvTransfer1LogView(generic.TemplateView):
    template_name = 'wms_skk/transfer1_log.html'

    def get_context_data(self, **kwargs):
        context = super(AgvTransfer1LogView, self).get_context_data(**kwargs)
        table = AgvTransfer1LogTable(AgvTransfer1.history.all())
        table.paginate(page=self.request.GET.get("page", 1), per_page=15)
        context['transfer1_log'] = table
        return context


@method_decorator([login_required, groups_required('Staff')], name='dispatch')
class AgvListView(generic.TemplateView):
    template_name = 'wms_skk/agv.html'

    def get_context_data(self, **kwargs):
        context = super(AgvListView, self).get_context_data(**kwargs)
        if 'storage_form' not in context:
            context['storage_form'] = StorageOrderForm()
        if 'retrieval_form' not in context:
            context['retrieval_form'] = RetrievalOrderForm()
        if 'move_form' not in context:
            context['move_form'] = MoveOrderForm()
        context['transfer1_db'] = AgvTransfer1.objects.all()
        context['plan_db'] = AgvProductionPlan.objects.all()
        context['queue1_db'] = AgvQueue1.objects.all()

        return context

    def post(self, request, *args, **kwargs):
        context = {}
        if 'storage' in request.POST:
            form = StorageOrderForm(request.POST)
            if form.is_valid():
                obj = AgvProductionPlan(product_id=Product.objects.get(product_id=request.POST.get('product_id', None)))
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
                    obj = AgvQueue1()
                    obj.product_id = obj_from.inv_product
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
                obj = AgvQueue1()
                obj.product_id = obj_from.inv_product
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
@csrf_exempt
def get_data_storage_form(request):
    data = {}
    if request.method == 'POST':
        obj = get_object_or_404(Product, product_id=request.POST.get('product_id', None))
        data['qty_storage'] = obj.qty_storage
        data['qty_storage_avail'] = obj.qty_storage_avail
        data['qty_limit'] = obj.qty_limit
        return JsonResponse(data)


@login_required
@csrf_exempt
def get_data_retrieval_form(request):
    data = {}
    if request.method == 'POST':
        obj = get_object_or_404(Product.objects.select_related('plant'), product_id=request.POST.get('product_id', None))

        # Calculate inventory qty #
        qs_inventory = Storage.objects.filter(inv_product=obj.product_id, storage_for=obj.product_id).exclude(storage_id__in=AgvQueue1.objects.filter(mode=2).values('pick_id'))
        inv_bag = qs_inventory.aggregate(models.Sum('inv_qty'))['inv_qty__sum']
        data['inv_bag'] = inv_bag if inv_bag else 0

        # Calculate available inventory qty #
        # Only retrieve from pre-assigned column and don't have misplace inventory before it #
        qs_avail_inventory = qs_inventory
        qs_misplace = Storage.objects.filter(~Q(storage_id__in=AgvQueue1.objects.filter(mode=2).values('pick_id')), ~Q(inv_product=obj.product_id), storage_for=obj.product_id,
                                             have_inventory=True)
        for column_id in qs_misplace.order_by().distinct().values_list('column_id', flat=True):
            misplace_outer = qs_misplace.filter(column_id=column_id).order_by('row').last()
            if misplace_outer:
                qs_avail_inventory = qs_avail_inventory.exclude(column_id=column_id, row__lte=misplace_outer.row)
        avail_inv_bag = qs_avail_inventory.aggregate(models.Sum('inv_qty'))['inv_qty__sum']
        data['avail_inv_bag'] = avail_inv_bag if avail_inv_bag else 0

        avail_inventory_zone_a = qs_avail_inventory.filter(zone='A').order_by('area', 'col', '-row')
        avail_inventory_zone_b = qs_avail_inventory.filter(zone='B').order_by('-area', '-col', '-row')
        pk_avail_inventory_list = list(avail_inventory_zone_a.values_list('storage_id', flat=True)) + list(avail_inventory_zone_b.values_list('storage_id', flat=True))

        # Calculate buffer qty #
        # Only store to pre-assigned buffer and don't have any inventory before it #
        qs_buffer = Storage.objects.filter(column_id__for_buffer__buffer_for_plant__plant_id=obj.plant.plant_id)
        qs_occupied = qs_buffer.filter(Q(have_inventory=True) | Q(storage_id__in=AgvQueue1.objects.all().values('place_id')))
        for column_id in qs_occupied.order_by().distinct().values_list('column_id', flat=True):
            occupied_outer = qs_occupied.filter(column_id=column_id).order_by('row').last()
            if occupied_outer:
                qs_buffer = qs_buffer.exclude(column_id=column_id, row__lte=occupied_outer.row)

        buffer_zone_a = qs_buffer.filter(zone='A').order_by('area', 'col', 'row')
        buffer_zone_b = qs_buffer.filter(zone='B').order_by('-area', '-col', 'row')
        pk_buffer_list = list(buffer_zone_a.values_list('storage_id', flat=True)) + list(buffer_zone_b.values_list('storage_id', flat=True))

        data['buffer_space'] = len(pk_buffer_list)
        data['buffer_list'] = pk_buffer_list

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
@csrf_exempt
def get_data_move_form(request):
    data = {}
    if request.method == 'POST':
        obj_from = get_object_or_404(Storage.objects.select_related('inv_product'), storage_id=request.POST.get('move_from', None))
        data['name_th'] = obj_from.inv_product.name_th
        data['product_id'] = obj_from.inv_product.product_id
        data['qty_bag'] = obj_from.inv_qty
        data['lot_name'] = obj_from.lot_name
        obj_to = get_object_or_404(Storage, storage_id=request.POST.get('move_to', None))
        data['storage_for'] = obj_to.storage_for
        return JsonResponse(data)


@login_required
@csrf_exempt
def get_data_agv_position(request):
    data = {}
    if request.method == 'GET':
        obj_transfer = get_object_or_404(AgvTransfer1, id=1)
        agv_x, agv_y, agv_beta = transfer_adjust(obj_transfer)
        agv_col, agv_row = position_cal(agv_x, agv_y)
        data['agv_col'] = agv_col
        data['agv_row'] = agv_row
        data['agv_beta'] = int(agv_beta)
        return JsonResponse(data)


class AutoCloseView(generic.TemplateView):
    template_name = 'wms_skk/autoclose.html'


@method_decorator(login_required, name='dispatch')
class PlanFormView(generic.TemplateView):
    template_name = 'wms_skk/agv/plan_form.html'


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

    template_name = 'wms_skk/agv/plan_update.html'
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


@login_required
def plan_delete(request, pk):
    obj = get_object_or_404(AgvProductionPlan, pk=pk)
    obj.changeReason = 'Manual Delete Production Plan'
    obj.delete()
    return redirect('wms_skk:auto_close')


@login_required
def plan_clear(request):
    obj = AgvProductionPlan.objects.all()
    obj.changeReason = 'Manual Delete Production Plan'
    obj.delete()
    return redirect(request.META.get('HTTP_REFERER'))


@method_decorator(login_required, name='dispatch')
class Queue1FormView(generic.TemplateView):
    template_name = 'wms_skk/agv/queue1_form.html'


@login_required
def queue1_update(request, pk):
    obj = get_object_or_404(AgvQueue1, pk=pk)
    data = {}
    if request.method == 'POST':
        form = AgvQueue1Form(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            if obj.mode == 1:
                pass
            elif obj.mode == 2:
                obj_from = get_object_or_404(Storage, storage_id=obj.pick_id)
                obj_to = get_object_or_404(Storage, storage_id=obj.place_id)
                obj.product_id = obj_from.inv_product
                obj.lot_name = obj_from.lot_name
                obj.qty_act = obj_from.inv_qty
                obj.created_on = obj_from.created_on
                obj.robot_no = None
                obj.pick_id = obj_from
                obj.place_id = obj_to
                obj.mode = 2
                obj.updated = 0
            obj.changeReason = 'Manual Update AGV1 Queue'
            obj.save()
            data['form_is_valid'] = True
        else:
            data['form_is_valid'] = False
    else:
        form = AgvQueue1Form(instance=obj)

    template_name = 'wms_skk/agv/queue1_update.html'
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


@login_required
def queue1_delete(request, pk):
    obj = get_object_or_404(AgvQueue1, pk=pk)
    obj.changeReason = 'Manual Delete AGV1 Queue'
    obj.delete()
    return redirect('wms_skk:auto_close')


@login_required
def queue1_clear(request):
    obj = AgvQueue1.objects.all()
    obj.changeReason = 'Manual Delete AGV1 Queue'
    obj.delete()
    return redirect(request.META.get('HTTP_REFERER'))


@method_decorator(login_required, name='dispatch')
class RobotFormView(generic.TemplateView):
    template_name = 'wms_skk/agv/robot_form.html'


@login_required
def robot_update(request, pk):
    obj = get_object_or_404(RobotQueue, pk=pk)
    data = {}
    if request.method == 'POST':
        form = RobotQueueForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.save()
            obj.changeReason = 'Manual Update Robot Queue'
            data['form_is_valid'] = True
        else:
            data['form_is_valid'] = False
    else:
        form = RobotQueueForm(instance=obj)

    template_name = 'wms_skk/agv/robot_update.html'
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


@login_required
def robot_delete(request, pk):
    obj = get_object_or_404(RobotQueue, pk=pk)
    obj.changeReason = 'Manual Delete Robot Queue'
    obj.delete()
    return redirect('wms_skk:auto_close')


@login_required
def robot_clear(request):
    obj = RobotQueue.objects.all()
    obj.changeReason = 'Manual Delete Robot Queue'
    obj.delete()
    return redirect(request.META.get('HTTP_REFERER'))


@method_decorator(login_required, name='dispatch')
class Transfer1FormView(generic.TemplateView):
    template_name = 'wms_skk/agv/transfer1_form.html'


@login_required
def transfer1_update(request):
    obj = get_object_or_404(AgvTransfer1, id=1)
    data = {}
    if request.method == 'POST':
        form = AgvTransfer1Form(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.save()
            obj.changeReason = 'Manual Update AGV1 Transfer'
            data['form_is_valid'] = True
        else:
            data['form_is_valid'] = False
    else:
        form = AgvTransfer1Form(instance=obj)

    template_name = 'wms_skk/agv/transfer1_update.html'
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)


@login_required
def transfer1_delete(request):
    obj = get_object_or_404(AgvTransfer1, id=1)
    obj.changeReason = 'Manual Delete AGV1 Transfer'
    obj.delete()


@login_required
def transfer1_clear(request):
    obj = AgvTransfer1.objects.all()
    obj.changeReason = 'Manual Delete AGV1 Transfer'
    obj.delete()
    return redirect(request.META.get('HTTP_REFERER'))


@method_decorator(login_required, name='dispatch')
class AgvTestListView(generic.TemplateView):
    template_name = 'wms_skk/agv_debug.html'

    def get_context_data(self, **kwargs):
        context = super(AgvTestListView, self).get_context_data(**kwargs)
        if 'storage_form' not in context:
            context['storage_form'] = StorageOrderForm()
        if 'robot_form' not in context:
            context['robot_form'] = RobotQueueForm()
        if 'manualtransfer_form' not in context:
            context['manualtransfer_form'] = ManualTransferForm()
        context['transfer1_db'] = AgvTransfer1.objects.all()
        context['plan_db'] = AgvProductionPlan.objects.all()
        context['robot_db'] = RobotQueue.objects.all()
        context['queue1_db'] = AgvQueue1.objects.all()

        return context

    def post(self, request, *args, **kwargs):
        context = {}
        if 'storage' in request.POST:
            form = StorageOrderForm(request.POST)
            if form.is_valid():
                obj = AgvProductionPlan(product_id=Product.objects.get(product_id=request.POST.get('product_id', None)))
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
                agv_no = 1
                runway_row = 9
                pattern = float(request.POST.get('pattern', None))
                robot_no = int(request.POST.get('robot_no_manual', None))
                obj_storage = get_object_or_404(Storage, storage_id=request.POST.get('place_id', None))

                qs_transfer = AgvTransfer1.objects.all()
                obj_transfer = get_object_or_404(qs_transfer)
                agv_x, agv_y, agv_beta = transfer_adjust(obj_transfer)

                if pattern != 2.0:
                    target_col = obj_storage.layout_col
                    target_row = obj_storage.layout_row
                elif pattern == 2.0:
                    target_col = 45 if robot_no == 1 else 40
                    target_row = runway_row

                route_calculate(agv_no, obj_transfer, pattern, agv_x, agv_y, target_col, target_row)

                obj = get_object_or_404(AgvTransfer1, id=1)
                obj.step = 1
                obj.changeReason = 'Manual Update AGV1 Transfer'
                obj.save()
                return redirect(request.META.get('HTTP_REFERER'))
            else:
                context['manualtransfer_form'] = form

        return render(request, self.template_name, self.get_context_data(**context))


@login_required
def agv1_to_home(request):
    agv_no = 1
    pattern = 0.0

    obj_transfer = get_object_or_404(AgvTransfer1.objects.all())
    agv_x, agv_y, agv_beta = transfer_adjust(obj_transfer)
    agv_col, agv_row = position_cal(agv_x, agv_y)

    # Home Location #
    target_col = 33
    target_row = 7 if agv_row != 7 else 8

    route_calculate(agv_no, obj_transfer, pattern, agv_x, agv_y, target_col, target_row)

    obj = get_object_or_404(AgvTransfer1, id=1)
    obj.step = 6
    obj.changeReason = 'Manual Update AGV1 Transfer'
    obj.save()
    return redirect(request.META.get('HTTP_REFERER'))
