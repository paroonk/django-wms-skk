from django import forms
from django.db.models import Q
from django.db.utils import ProgrammingError
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from .models import *


class InventoryForm(forms.ModelForm):
    inv_product = forms.ModelChoiceField(label=_('Inventory Product'), queryset=Product.objects.none(), empty_label=None)
    inv_qty = forms.IntegerField(label=_('Inventory Quantity (Bag)'))
    lot_name = forms.CharField(label=_('Lot Name'), required=False)
    created_on = forms.DateTimeField(label=_('Created On'), input_formats=['%d/%m/%Y %H:%M:%S'], required=False)

    def clean_inv_qty(self):
        data = self.cleaned_data['inv_qty']
        if data <= 0:
            raise forms.ValidationError(_('Quantity must be more than 0 bag.'))
        return data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['inv_product'].queryset = Product.objects.all()

    class Meta:
        model = Storage
        fields = ['inv_product', 'inv_qty', 'lot_name', 'created_on']


class InventoryColumnForm(forms.Form):
    column_id = forms.CharField(widget=forms.HiddenInput())
    inv_product = forms.ModelChoiceField(label=_('Inventory Product'), queryset=Product.objects.none(), empty_label=None)
    inv_qty = forms.IntegerField(label=_('Inventory Quantity (Bag)'))
    lot_name = forms.CharField(label=_('Lot Name'), required=False)
    created_on = forms.DateTimeField(label=_('Created On'), input_formats=['%d/%m/%Y %H:%M:%S'], required=False)

    def clean_inv_qty(self):
        data = self.cleaned_data['inv_qty']
        if data <= 0:
            raise forms.ValidationError(_('Quantity must be more than 0 bag.'))
        return data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['inv_product'].queryset = Product.objects.all()


class ColumnForm(forms.ModelForm):
    is_inventory = forms.ChoiceField(label=_('Is Inventory?'), choices=Column.is_inventory_choices)
    for_product = forms.ModelChoiceField(label=_('Product'), queryset=Product.objects.none(), required=False)
    for_buffer = forms.ModelChoiceField(label=_('Buffer'), queryset=Buffer.objects.none(), required=False)

    def clean_for_product(self):
        data = self.cleaned_data['for_product']
        if self.cleaned_data['is_inventory'] == 'True' and data is None:
            raise forms.ValidationError(_('This field is required'))
        return data

    def clean_for_buffer(self):
        data = self.cleaned_data['for_buffer']
        if self.cleaned_data['is_inventory'] == 'False' and data is None:
            raise forms.ValidationError(_('This field is required'))
        return data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['for_product'].queryset = Product.objects.all()
        self.fields['for_buffer'].queryset = Buffer.objects.all()

    class Meta:
        model = Column
        fields = ['is_inventory', 'for_product', 'for_buffer']


class StorageOrderForm(forms.Form):
    product_name_storage = forms.ModelChoiceField(label=_('Product Name'), queryset=Product.objects.none(), empty_label=None)
    qty_storage = forms.IntegerField(label=_('Total Storage (Bag)'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    qty_storage_avail = forms.IntegerField(label=_('Available Storage (Bag)'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    qty_bag = forms.IntegerField(label=_('Quantity (Bag)'))
    qty_pallet = forms.IntegerField(label=_('Quantity (Pallet)'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    lot_name = forms.CharField(label=_('Lot Name'), required=False)

    def clean_qty_bag(self):
        data = self.cleaned_data['qty_bag']
        if data <= 0:
            raise forms.ValidationError(_('Quantity must be more than 0 bag.'))
        elif data > self.cleaned_data['qty_storage_avail']:
            raise forms.ValidationError(_('Available storage not enough. Quantity must be less than or equal {} bags.').format(self.cleaned_data['qty_storage_avail']))
        return data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product_name_storage'].queryset = Product.objects.all()


class RetrievalOrderForm(forms.Form):
    product_name_retrieve = forms.ModelChoiceField(label=_('Product Name'), queryset=Product.objects.none(), empty_label=None)
    inv_bag = forms.IntegerField(label=_('Inventory (Bag)'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    avail_inv_bag = forms.IntegerField(label=_('Available Inventory (Bag)'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    buffer_space = forms.IntegerField(label=_('Buffer Space (Pallet)'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    qty_bag = forms.IntegerField(label=_('Retrieve Quantity (Bag)'))
    qty_act_bag = forms.IntegerField(label=_('Actual Quantity (Bag)'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    qty_act_pallet = forms.IntegerField(label=_('Actual Quantity (Pallet)'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    retrieve_list = forms.CharField(widget=forms.HiddenInput())
    buffer_list = forms.CharField(widget=forms.HiddenInput())

    def clean_qty_bag(self):
        data = self.cleaned_data['qty_bag']
        if data <= 0:
            raise forms.ValidationError(_('Quantity must be more than 0 bag.'))
        elif data > self.cleaned_data['avail_inv_bag']:
            raise forms.ValidationError(_('Available inventory not enough. Quantity must be less than or equal {} bags.').format(self.cleaned_data['avail_inv_bag']))
        return data

    def clean_qty_act_pallet(self):
        data = self.cleaned_data['qty_act_pallet']
        if data > self.cleaned_data['buffer_space']:
            raise forms.ValidationError(_('Buffer space not enough. Quantity must be less than or equal {} pallets. Change retrieve quantity and try again.').format(self.cleaned_data['buffer_space']))
        return data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product_name_retrieve'].queryset = Product.objects.all()


class MoveOrderForm(forms.Form):
    move_from = forms.ModelChoiceField(label=_('From'), queryset=Storage.objects.none(), empty_label=None)
    product_name_move = forms.CharField(label=_('Product Name'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    qty_bag = forms.IntegerField(label=_('Quantity (Bag)'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    lot_name = forms.CharField(label=_('Lot Name'), required=False, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    move_to = forms.ModelChoiceField(label=_('To'), queryset=Storage.objects.none(), empty_label=None)
    storage_for = forms.CharField(label=_('Storage For'), widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    def clean_move_from(self):
        data = self.cleaned_data['move_from']
        if not get_object_or_404(Storage, storage_id=self.cleaned_data['move_from']).have_inventory:
            raise forms.ValidationError(_('No inventory in selected storage. Refresh the page, and try again.'))
        return data

    def clean_move_to(self):
        data = self.cleaned_data['move_to']
        if get_object_or_404(Storage, storage_id=self.cleaned_data['move_to']).have_inventory:
            raise forms.ValidationError(_('Selected storage already have another inventory. Refresh the page, and try again.'))
        return data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs_queue_pick_id = AgvQueue.objects.filter(mode=2)
        qs_avail_inventory = Storage.objects.filter(have_inventory=True).exclude(storage_id__in=qs_queue_pick_id.values('pick_id'))
        for column_id in qs_avail_inventory.order_by().distinct().values_list('column_id', flat=True):
            inventory_outer = qs_avail_inventory.filter(column_id=column_id).order_by('row').last()
            if inventory_outer:
                qs_avail_inventory = qs_avail_inventory.exclude(column_id=column_id, row__lt=inventory_outer.row)
        self.fields['move_from'].queryset = qs_avail_inventory

        qs_queue_place_id = AgvQueue.objects.all()
        qs_avail_storage = Storage.objects.filter(have_inventory=False)
        qs_occupied = Storage.objects.filter(Q(have_inventory=True) | Q(storage_id__in=qs_queue_place_id.values('place_id')))
        for column_id in qs_avail_storage.order_by().distinct().values_list('column_id', flat=True):
            occupied_outer = qs_occupied.filter(column_id=column_id).order_by('row').last()
            if occupied_outer:
                qs_avail_storage = qs_avail_storage.exclude(column_id=column_id, row__lte=occupied_outer.row)
        self.fields['move_to'].queryset = qs_avail_storage


class AgvProductionPlanForm(forms.ModelForm):
    product_name = forms.ModelChoiceField(label=_('Product Name'), queryset=Product.objects.none(), empty_label=None)
    lot_name = forms.CharField(label=_('Lot Name'), required=False)
    qty_total = forms.IntegerField(label=_('Total Quantity (Bag)'))
    qty_remain = forms.IntegerField(label=_('Remaining Quantity (Bag)'))

    def clean_qty_total(self):
        data = self.cleaned_data['qty_total']
        if data <= 0:
            raise forms.ValidationError(_("Quantity must be more than 0 bag."))
        return data

    def clean_qty_remain(self):
        data = self.cleaned_data['qty_remain']
        if data <= 0:
            raise forms.ValidationError(_('Quantity must be more than 0 bag.'))
        elif self.data.get('qty_total') == '':
            raise forms.ValidationError(_('Check total quantity input.'))
        elif data > self.cleaned_data['qty_total']:
            raise forms.ValidationError(_('Quantity must be less than or equal {} pallets.').format(self.cleaned_data['qty_total']))
        return data

    class Meta:
        model = AgvProductionPlan
        fields = ['product_name', 'lot_name', 'qty_total', 'qty_remain']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product_name'].queryset = Product.objects.all()


class RobotQueueForm(forms.ModelForm):
    robot_no = forms.ChoiceField(label=_('Robot No.'), choices=RobotQueue.robot_choices, required=False)
    product_id = forms.ChoiceField(label=_('Product Name'), choices=RobotQueue.product_id_choices)
    qty_act = forms.IntegerField(label=_('Actual Quantity (Bag)'))
    updated = forms.ChoiceField(label=_('Status'), choices=RobotQueue.updated_choices, initial=1)

    def clean_qty_act(self):
        data = self.cleaned_data['qty_act']
        if data <= 0:
            raise forms.ValidationError(_('Quantity must be more than 0 bag.'))
        return data

    class Meta:
        model = RobotQueue
        fields = ['robot_no', 'product_id', 'qty_act', 'updated']


class AgvQueueForm(forms.ModelForm):
    mode = forms.ChoiceField(label=_('Mode'), choices=AgvQueue.mode_choices)
    robot_no = forms.ChoiceField(label=_('Robot No.'), choices=RobotQueue.robot_choices, required=False)
    pick_id = forms.ModelChoiceField(label=_('From'), queryset=Storage.objects.none(), required=False)
    place_id = forms.ModelChoiceField(label=_('To'), queryset=Storage.objects.none())

    def clean_robot_no(self):
        data = self.cleaned_data['robot_no']
        if self.cleaned_data['mode'] == 1 and data is None:
            raise forms.ValidationError(_('This field is required in storage mode.'))
        return data

    def clean_pick_id(self):
        data = self.cleaned_data['pick_id']
        if self.cleaned_data['mode'] == 2 and data is None:
            raise forms.ValidationError(_('This field is required in retrieval/move mode.'))
        return data

    class Meta:
        model = AgvQueue
        fields = ['mode', 'robot_no', 'pick_id', 'place_id', 'agv_no']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.mode == 1:
            qs_queue_pick_id = AgvQueue.objects.filter(mode=2)
        elif self.instance.mode == 2:
            qs_queue_pick_id = AgvQueue.objects.filter(mode=2).exclude(pick_id=self.instance.pick_id.storage_id)
        qs_avail_inventory = Storage.objects.filter(have_inventory=True).exclude(storage_id__in=qs_queue_pick_id.values('pick_id'))
        self.fields['pick_id'].queryset = qs_avail_inventory

        qs_queue_place_id = AgvQueue.objects.exclude(place_id=self.instance.place_id.storage_id)
        qs_avail_storage = Storage.objects.filter(have_inventory=False)
        self.fields['place_id'].queryset = qs_avail_storage


class AgvTransferForm(forms.ModelForm):
    status = forms.ChoiceField(label=_('AGV Status'), choices=AgvTransfer.status_choices)
    step = forms.ChoiceField(label=_('Step'), choices=AgvTransfer.step_choices)
    pause = forms.ChoiceField(label=_('Pause'), choices=AgvTransfer.pause_choices)
    pattern = forms.ChoiceField(label=_('Pattern'), choices=AgvTransfer.pattern_choices)

    class Meta:
        model = AgvTransfer
        fields = ['status', 'step', 'pause', 'pattern']


class ManualTransferForm(forms.Form):
    agv_no = forms.ModelChoiceField(label=_('AGV No.'), queryset=AgvTransfer.objects.all(), empty_label=None)
    pattern = forms.ChoiceField(label=_('Pattern'), choices=AgvTransfer.pattern_choices)
    layout_col = forms.ChoiceField(label=_('Column'), choices=[(col, col) for col in list(set(Coordinate.objects.all().values_list('layout_col', flat=True)))[1:-1]])
    layout_row = forms.ChoiceField(label=_('Row'), choices=[(row, row) for row in list(set(Coordinate.objects.all().values_list('layout_row', flat=True)))[1:-1]])

    def clean(self):
        cleaned_data = super().clean()
        layout_col = cleaned_data.get('layout_col')
        layout_row = cleaned_data.get('layout_row')

        if not Coordinate.objects.filter(layout_col=layout_col, layout_row=layout_row).exists():
            raise forms.ValidationError(_('Selected coordinate not exist'))


class HistoryGraphForm(forms.Form):
    try:
        plant_list = list(Plant.objects.all().values_list('plant_id', flat=True))
    except ProgrammingError:
        plant_list = []
    label_choices = [('all', _('All'))] + [(plant, plant) for plant in plant_list]
    label = forms.ChoiceField(label=_('Data'), choices=label_choices)
    date_filter = forms.CharField(label=_('Date'))
    data = forms.IntegerField(label=_('Number of Data'), min_value=1, max_value=100)


class LogFilterForm(forms.Form):
    date_filter = forms.CharField(label=_('Date'))
