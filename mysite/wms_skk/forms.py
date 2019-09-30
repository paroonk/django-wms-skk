from django import forms
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import *


class CustomModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name_th


class InventoryForm(forms.ModelForm):
    inv_product = CustomModelChoiceField(label='Inventory Product', queryset=Product.objects.none(), empty_label=None)
    inv_qty = forms.IntegerField(label='Inventory Quantity (Bag)')

    def clean_inv_qty(self):
        data = self.cleaned_data['inv_qty']
        if data <= 0:
            raise forms.ValidationError('Quantity must be more than 0 bag.')
        return data

    def __init__(self, *args, **kwargs):
        super(InventoryForm, self).__init__(*args, **kwargs)
        self.fields['inv_product'].queryset = Product.objects.all()

    class Meta:
        model = Storage
        fields = ['inv_product', 'inv_qty', 'lot_name']


class StorageOrderForm(forms.Form):
    name_th_storage = CustomModelChoiceField(label='Product Name', queryset=Product.objects.none(), empty_label=None)
    product_id = forms.CharField(label='Product ID', widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    qty_storage = forms.IntegerField(label='Total Storage (Bag)', widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    qty_storage_avail = forms.IntegerField(label='Available Storage (Bag)', widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    qty_bag = forms.IntegerField(label='Quantity (Bag)')
    qty_pallet = forms.IntegerField(label='Quantity (Pallet)', widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    lot_name = forms.CharField(label='Lot Name', required=False)

    def clean_qty_bag(self):
        data = self.cleaned_data['qty_bag']
        if data <= 0:
            raise forms.ValidationError('Quantity must be more than 0 bag.')
        elif data > self.cleaned_data['qty_storage_avail']:
            raise forms.ValidationError('Quantity must be less than or equal {} bags.'.format(self.cleaned_data['qty_storage_avail']))
        return data

    def __init__(self, *args, **kwargs):
        super(StorageOrderForm, self).__init__(*args, **kwargs)
        self.fields['name_th_storage'].queryset = Product.objects.all()


class RetrievalOrderForm(forms.Form):
    name_th_retrieve = CustomModelChoiceField(label='Product Name', queryset=Product.objects.none(), empty_label=None)
    product_id = forms.CharField(label='Product ID', widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    inv_bag = forms.IntegerField(label='Inventory (Bag)', widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    avail_inv_bag = forms.IntegerField(label='Available Inventory (Bag)', widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    buffer_space = forms.IntegerField(label='Buffer Space (Pallet)', widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    qty_bag = forms.IntegerField(label='Retrieve Quantity (Bag)')
    qty_act_bag = forms.IntegerField(label='Actual Quantity (Bag)', widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    qty_act_pallet = forms.IntegerField(label='Actual Quantity (Pallet)', widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    retrieve_list = forms.CharField(widget=forms.HiddenInput())
    buffer_list = forms.CharField(widget=forms.HiddenInput())

    def clean_qty_bag(self):
        data = self.cleaned_data['qty_bag']
        if data <= 0:
            raise forms.ValidationError('Quantity must be more than 0 pallet.')
        elif data > self.cleaned_data['avail_inv_bag']:
            raise forms.ValidationError('Quantity must be less than or equal {} pallets.'.format(self.cleaned_data['avail_inv_bag']))
        return data

    def clean_qty_act_pallet(self):
        data = self.cleaned_data['qty_act_pallet']
        if data > self.cleaned_data['buffer_space']:
            raise forms.ValidationError('Quantity must be less than or equal {} pallets. Change retrieve quantity and try again.'.format(self.cleaned_data['buffer_space']))
        return data

    def __init__(self, *args, **kwargs):
        super(RetrievalOrderForm, self).__init__(*args, **kwargs)
        self.fields['name_th_retrieve'].queryset = Product.objects.all()


class MoveOrderForm(forms.Form):
    move_from = forms.ModelChoiceField(label='From', queryset=Storage.objects.none(), empty_label=None)
    name_th = forms.CharField(label='Product Name', widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    product_id = forms.CharField(label='Product ID', widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    qty_bag = forms.IntegerField(label='Quantity (Bag)', widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    lot_name = forms.CharField(label='Lot Name', required=False, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    move_to = forms.ModelChoiceField(label='To', queryset=Storage.objects.none(), empty_label=None)
    storage_for = forms.CharField(label='Storage For', widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    def clean_move_from(self):
        data = self.cleaned_data['move_from']
        if not get_object_or_404(Storage, storage_id=self.cleaned_data['move_from']).have_inventory:
            raise forms.ValidationError('No inventory in selected storage. Refresh the page, and try again.')
        return data

    def clean_move_to(self):
        data = self.cleaned_data['move_to']
        if get_object_or_404(Storage, storage_id=self.cleaned_data['move_to']).have_inventory:
            raise forms.ValidationError('Selected storage already have another inventory. Refresh the page, and try again.')
        return data

    def __init__(self, *args, **kwargs):
        super(MoveOrderForm, self).__init__(*args, **kwargs)
        qs_queue_pick_id = AgvQueue1.objects.filter(mode=2)
        qs_avail_inventory = Storage.objects.filter(have_inventory=True).exclude(storage_id__in=qs_queue_pick_id.values('pick_id'))
        for column_id in qs_avail_inventory.order_by().distinct().values_list('column_id', flat=True):
            inventory_outer = qs_avail_inventory.filter(column_id=column_id).order_by('row').last()
            if inventory_outer:
                qs_avail_inventory = qs_avail_inventory.exclude(column_id=column_id, row__lt=inventory_outer.row)
        self.fields['move_from'].queryset = qs_avail_inventory

        qs_queue_place_id = AgvQueue1.objects.all()
        qs_avail_storage = Storage.objects.filter(have_inventory=False)
        qs_occupied = Storage.objects.filter(Q(have_inventory=True) | Q(storage_id__in=qs_queue_place_id.values('place_id')))
        for column_id in qs_avail_storage.order_by().distinct().values_list('column_id', flat=True):
            occupied_outer = qs_occupied.filter(column_id=column_id).order_by('row').last()
            if occupied_outer:
                qs_avail_storage = qs_avail_storage.exclude(column_id=column_id, row__lte=occupied_outer.row)
        self.fields['move_to'].queryset = qs_avail_storage


class AgvProductionPlanForm(forms.ModelForm):
    product_id = CustomModelChoiceField(label='Product Name', queryset=Product.objects.none(), empty_label=None)

    def clean_qty_total(self):
        data = self.cleaned_data['qty_total']
        if data <= 0:
            raise forms.ValidationError("Quantity must be more than 0 bag.")
        return data

    def clean_qty_remain(self):
        data = self.cleaned_data['qty_remain']
        if data <= 0:
            raise forms.ValidationError('Quantity must be more than 0 bag.')
        elif self.data.get('qty_total') == '':
            raise forms.ValidationError('Check total quantity input.')
        elif data > self.cleaned_data['qty_total']:
            raise forms.ValidationError('Quantity must be less than or equal {} pallets.'.format(self.cleaned_data['qty_total']))
        return data

    class Meta:
        model = AgvProductionPlan
        fields = ['product_id', 'lot_name', 'qty_total', 'qty_remain']

    def __init__(self, *args, **kwargs):
        super(AgvProductionPlanForm, self).__init__(*args, **kwargs)
        self.fields['product_id'].queryset = Product.objects.all()


class AgvQueue1Form(forms.ModelForm):
    pick_id = forms.ModelChoiceField(label='From', queryset=Storage.objects.none(), required=False)
    place_id = forms.ModelChoiceField(label='To', queryset=Storage.objects.none())

    def clean_robot_no(self):
        data = self.cleaned_data['robot_no']
        if self.cleaned_data['mode'] == 1 and data is None:
            raise forms.ValidationError('This field is required in storage mode.')
        return data

    def clean_pick_id(self):
        data = self.cleaned_data['pick_id']
        if self.cleaned_data['mode'] == 2 and data is None:
            raise forms.ValidationError('This field is required in retrieval/move mode.')
        return data

    class Meta:
        model = AgvQueue1
        fields = ['mode', 'robot_no', 'pick_id', 'place_id']

    def __init__(self, *args, **kwargs):
        super(AgvQueue1Form, self).__init__(*args, **kwargs)
        if self.instance.mode == 1:
            qs_queue_pick_id = AgvQueue1.objects.filter(mode=2)
        elif self.instance.mode == 2:
            qs_queue_pick_id = AgvQueue1.objects.filter(mode=2).exclude(pick_id=self.instance.pick_id.storage_id)
        qs_avail_inventory = Storage.objects.filter(have_inventory=True).exclude(storage_id__in=qs_queue_pick_id.values('pick_id'))
        self.fields['pick_id'].queryset = qs_avail_inventory

        qs_queue_place_id = AgvQueue1.objects.exclude(place_id=self.instance.place_id.storage_id)
        qs_avail_storage = Storage.objects.filter(have_inventory=False)
        self.fields['place_id'].queryset = qs_avail_storage


class RobotQueueForm(forms.ModelForm):
    robot_choices = [(1, 'Robot #1'), (2, 'Robot #2')]
    robot_no = forms.ChoiceField(choices=robot_choices, required=False)
    updated_choices = [(0, 'Wait'), (1, 'Ready')]
    updated = forms.ChoiceField(choices=updated_choices, initial=1)

    def clean_qty_act(self):
        data = self.cleaned_data['qty_act']
        if data <= 0:
            raise forms.ValidationError('Quantity must be more than 0 bag.')
        return data

    class Meta:
        model = RobotQueue
        fields = ['robot_no', 'qty_act', 'updated']


class AgvTransfer1Form(forms.ModelForm):
    class Meta:
        model = AgvTransfer1
        fields = ['status', 'step', 'pause', 'pattern']


class ManualTransferForm(forms.Form):
    pattern_choices = [(0.0, 'P0: ArmRun->Rev'), (1.0, 'P1: Rev->ArmRun'), (2.0, 'P2: ArmPick->FW->Pick(Robot)'), (3.0, 'P3: ArmPick->FW->Pick(Storage)'), (4.0, 'P4: FW->Put')]
    pattern = forms.ChoiceField(choices=pattern_choices)
    robot_choices = [(1, 'Robot #1'), (2, 'Robot #2')]
    robot_no_manual = forms.ChoiceField(label='Robot No.', choices=robot_choices, required=False)
    place_id = forms.ModelChoiceField(label='To', queryset=Storage.objects.all(), empty_label=None)

    def clean_robot_no_manual(self):
        data = self.cleaned_data['robot_no_manual']
        if self.cleaned_data['pattern'] == 2.0 and data is None:
            raise forms.ValidationError('This field is required in {}'.format(self.pattern_choices[self.cleaned_data['pattern']]))
        return data

    def clean_place_id(self):
        data = self.cleaned_data['place_id']
        if self.cleaned_data['pattern'] != 2.0 and data is None:
            raise forms.ValidationError('This field is required in {}'.format(self.pattern_choices[self.cleaned_data['pattern']]))
        return data
