from computedfields.models import ComputedFieldsModel, computed
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class Plant(ComputedFieldsModel):
    plant_id = models.CharField(max_length=10, primary_key=True, unique=True)
    description = models.CharField(max_length=100)

    def __str__(self):
        return self.plant_id

    class Meta:
        ordering = ('plant_id',)


class Buffer(ComputedFieldsModel):
    buffer_id = models.CharField(max_length=10, primary_key=True, unique=True)
    buffer_for_plant = models.ManyToManyField(Plant)

    def buffer_for_plant_list(self):
        return ", ".join([plant.plant_id for plant in self.buffer_for_plant.all()])

    def __str__(self):
        return self.buffer_id

    class Meta:
        ordering = ('buffer_id',)


class Product(ComputedFieldsModel):
    product_name = models.CharField(max_length=100, primary_key=True, unique=True, verbose_name=_('Product Name'))
    plant = models.ForeignKey(Plant, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('Plant'))
    qty_limit = models.PositiveIntegerField(verbose_name=_('Per Pallet Quantity'))
    bg_color = models.CharField(max_length=10, verbose_name=_('Background Color'))
    font_color = models.CharField(max_length=10, verbose_name=_('Font Color'))
    qty_storage = models.PositiveIntegerField(blank=True, null=True, verbose_name=_('Storage Qty'))
    qty_inventory = models.PositiveIntegerField(blank=True, null=True, verbose_name=_('Inventory Qty'))
    qty_buffer = models.PositiveIntegerField(blank=True, null=True, verbose_name=_('Buffer Qty'))
    qty_misplace = models.PositiveIntegerField(blank=True, null=True, verbose_name=_('Misplace Qty'))
    qty_total = models.PositiveIntegerField(blank=True, null=True, verbose_name=_('Total Qty'))
    qty_storage_avail = models.IntegerField(blank=True, null=True, verbose_name=_('Avail. Storage Qty'))
    qty_inventory_avail = models.IntegerField(blank=True, null=True, verbose_name=_('Avail. Inventory Qty'))
    history = HistoricalRecords(excluded_fields=['name_eng', 'plant', 'qty_limit', 'bg_color', 'font_color'])

    def __str__(self):
        return self.product_name

    class Meta:
        ordering = ('plant', 'product_name')


class Column(ComputedFieldsModel):
    column_id = models.CharField(max_length=10, primary_key=True, unique=True)
    is_inventory_choices = [(True, _('Inventory')), (False, _('Buffer'))]
    is_inventory = models.BooleanField(choices=is_inventory_choices)
    for_product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True)
    for_buffer = models.ForeignKey(Buffer, on_delete=models.SET_NULL, blank=True, null=True)

    @computed(models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Storage For')))
    def storage_for(self):
        try:
            return self.for_product.product_name if self.is_inventory else self.for_buffer.buffer_id
        except:
            return None

    def save(self, *args, **kwargs):
        if self.is_inventory:
            self.for_buffer = None
        else:
            self.for_product = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.column_id

    class Meta:
        ordering = ('column_id',)


class Coordinate(ComputedFieldsModel):
    coor_id = models.AutoField(primary_key=True, unique=True)
    layout_col = models.PositiveSmallIntegerField(default=1)
    layout_row = models.PositiveSmallIntegerField(default=1)
    coor_x = models.FloatField()
    coor_y = models.FloatField()

    def __str__(self):
        return 'Col={} Row={}'.format(self.layout_col, self.layout_row)

    class Meta:
        ordering = ('coor_id',)


class Storage(ComputedFieldsModel):
    storage_id = models.CharField(max_length=10, primary_key=True, unique=True, verbose_name=_('Storage ID'))
    layout_col = models.PositiveSmallIntegerField(default=1, verbose_name=_('Layout Col'))
    layout_row = models.PositiveSmallIntegerField(default=1, verbose_name=_('Layout Row'))
    column_id = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('Column ID'))
    coor_id = models.ForeignKey(Coordinate, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('Coordinate ID'))
    inv_product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('Inventory Product'))
    inv_qty = models.PositiveIntegerField(blank=True, null=True, verbose_name=_('Inventory Quantity (Bag)'))
    lot_name = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Lot Name'))
    created_on = models.DateTimeField(blank=True, null=True, verbose_name=_('Created On'))
    updated_on = models.DateTimeField(blank=True, null=True, verbose_name=_('Updated On'))
    history = HistoricalRecords(excluded_fields=['layout_col', 'layout_row', 'column_id', 'coor_id', 'lot_name', 'updated_on', 'zone', 'col', 'row', 'coor_x', 'coor_y', 'bg_color', 'font_color'])

    @computed(models.CharField(max_length=1, verbose_name=_('Zone')))
    def zone(self):
        return str(self.storage_id)[0:1]

    @computed(models.CharField(max_length=2, verbose_name=_('Column No.')))
    def col(self):
        return str(self.storage_id)[1:3]

    @computed(models.CharField(max_length=3, verbose_name=_('Row No.')))
    def row(self):
        return str(self.storage_id)[3:6]

    @computed(models.FloatField(verbose_name=_('Coordinate X')), depends=['coor_id#layout_col', 'coor_id#layout_row', 'coor_id#coor_x', 'coor_id#coor_y'])
    def coor_x(self):
        try:
            return self.coor_id.coor_x
        except:
            return 0.0

    @computed(models.FloatField(verbose_name=_('Coordinate Y')), depends=['coor_id#layout_col', 'coor_id#layout_row', 'coor_id#coor_x', 'coor_id#coor_y'])
    def coor_y(self):
        try:
            return self.coor_id.coor_y
        except:
            return 0.0

    @computed(models.BooleanField(verbose_name=_('Is Inventory')), depends=['column_id#is_inventory'])
    def is_inventory(self):
        return self.column_id.is_inventory

    @computed(models.CharField(max_length=100, blank=True, null=True, verbose_name='Storage For'), depends=['column_id#storage_for'])
    def storage_for(self):
        return self.column_id.storage_for

    @computed(models.BooleanField(verbose_name=_('Have Inventory')))
    def have_inventory(self):
        return True if self.inv_product else False

    @computed(models.CharField(max_length=10, verbose_name=_('Bg Color')), depends=['inv_product#bg_color'])
    def bg_color(self):
        try:
            return self.inv_product.bg_color
        except:
            return 'white'

    @computed(models.CharField(max_length=10, verbose_name=_('Font Color')), depends=['inv_product#font_color'])
    def font_color(self):
        try:
            return self.inv_product.font_color
        except:
            return 'black'

    @computed(models.BooleanField(blank=True, null=True, verbose_name=_('Misplace')), depends=['column_id#storage_for'])
    def misplace(self):
        try:
            return True if self.is_inventory and self.inv_product.product_name != self.storage_for else False
        except:
            return False

    def save(self, *args, **kwargs):
        try:
            self.column_id = Column.objects.get(column_id=str(self.storage_id)[0:3])
        except:
            self.column_id = None
        try:
            self.coor_id = Coordinate.objects.get(layout_col=self.layout_col, layout_row=self.layout_row)
        except:
            self.coor_id = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.storage_id

    class Meta:
        ordering = ('storage_id',)


class AgvProductionPlan(ComputedFieldsModel):
    product_name = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True, null=True, verbose_name=_('Plan Product'))
    qty_total = models.PositiveIntegerField(verbose_name=_('Total Quantity (Bag)'))
    qty_remain = models.PositiveIntegerField(verbose_name=_('Remaining Quantity (Bag)'))
    lot_name = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Lot Name'))
    history = HistoricalRecords()

    @property
    def percent_complete(self):
        return "{:.2%}".format(1 - (self.qty_remain / self.qty_total))

    def __str__(self):
        return '{}'.format(self.id)

    class Meta:
        ordering = ('id',)


class RobotStatus(ComputedFieldsModel):
    robot_no = models.PositiveSmallIntegerField(primary_key=True, unique=True, verbose_name=_('Robot No.'))
    brand = models.PositiveSmallIntegerField(blank=True, null=True, default=1, verbose_name=_('Brand No.'))
    qty_act = models.PositiveIntegerField(blank=True, null=True, default=1, verbose_name=_('Actual Quantity (Bag)'))
    qty_target = models.PositiveIntegerField(blank=True, null=True, default=1, verbose_name=_('Target Quantity (Bag)'))

    def __str__(self):
        return '{}'.format(self.robot_no)

    class Meta:
        ordering = ('robot_no',)
        verbose_name_plural = 'Robot status'


class RobotQueue(ComputedFieldsModel):
    robot_choices = [(1, _('Robot #1')), (2, _('Robot #2'))]
    robot_no = models.PositiveSmallIntegerField(choices=robot_choices, verbose_name=_('Robot No.'))
    product_id_choices = list(
        enumerate(
            [
                'ซูเปอร์ซีเมนต์ SKK',
                'ช้างงานโครงสร้าง สูตรไฮบริด SKK',
                'ช้างงานโครงสร้าง SKK',
                'เสือฉาบสูตรพิเศษ SKK',
                'แรด SKK',
                'เสือ SKK',
                'ช้างงานหล่อ SKK',
                'ซูเปอร์ซีเมนต์ KCL',
                'เสือฉาบสูตรพิเศษ KCL',
                'ช้างงานโครงสร้าง KCL',
                'SMC KK1 ฉาบอิฐมวลเบา',
                'SMC KK1 ฉาบทั่วไป',
                'SMC KK1 ฉาบอิฐมวลเบา สูตรเอ็กซ์เพิร์ท',
                'SMC KK2 DURA ONE ฉาบอิฐมวลเบา',
                'SMC KK2 ก่อทั่วไป',
                'SMC KK2 เทปรับพื้น',
                'SMC KK2 อีซี่',
                'SMC KK2 ฉาบทั่วไป',
                'SMC KK2 ฉาบอิฐมวลเบา',
                'SMC BB ฉาบทั่วไป',
                'SMC BB ฉาบอิฐมวลเบา',
                'SMC BB ก่อทั่วไป',
                'SMC NR DURA ONE ฉาบอิฐมวลเบา',
                'SMC NR ฉาบทั่วไป',
                'SMC NR ฉาบอิฐมวลเบา',
                'DURA ONE SKK (เขียว) ก่อ ฉาบ เท',
                'DURA ONE SKK (แดง) งานโครงสร้าง',
                'SMC LP ฉาบทั่วไป',
                'SMC LP ฉาบอิฐมวลเบา',
                'SMC KK1 ฉาบทั่วไป สูตรเอ็กซ์เพิร์ท',
                'Montania C-150 (42.63 kg)',
                'SMC KK2 เทปรับพื้น',
            ]
        )
    )
    product_id = models.PositiveSmallIntegerField(choices=product_id_choices, blank=True, null=True, verbose_name=_('Product ID'))
    qty_act = models.PositiveIntegerField(verbose_name=_('Actual Quantity (Bag)'))
    updated_choices = [(0, _('Wait')), (1, _('Ready'))]
    updated = models.PositiveSmallIntegerField(choices=updated_choices, verbose_name=_('Updated'))
    history = HistoricalRecords()

    def __str__(self):
        return '{}'.format(self.id)

    class Meta:
        ordering = ('id',)


class AgvQueue(ComputedFieldsModel):
    product_name = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True, null=True, verbose_name=_('Queuing Product'))
    lot_name = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Lot Name'))
    qty_act = models.PositiveIntegerField(verbose_name=_('Actual Quantity (Bag)'))
    created_on = models.DateTimeField(blank=True, null=True, verbose_name=_('Created On'))
    robot_choices = list(enumerate([_('Robot #1'), _('Robot #2')], start=1))
    robot_no = models.PositiveSmallIntegerField(choices=robot_choices, blank=True, null=True, verbose_name=_('Robot No.'))
    pick_id = models.ForeignKey(Storage, on_delete=models.CASCADE, blank=True, null=True, verbose_name=_('Pick ID'), related_name='pick_id')
    place_id = models.ForeignKey(Storage, on_delete=models.CASCADE, blank=True, null=True, verbose_name=_('Place ID'), related_name='place_id')
    mode_choices = list(enumerate([_('Storage'), _('Retrieval/Move')], start=1))
    mode = models.PositiveSmallIntegerField(choices=mode_choices, verbose_name=_('Mode'))
    agv_no = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name=_('AGV No.'))
    history = HistoricalRecords()

    @computed(models.PositiveSmallIntegerField(blank=True, null=True, verbose_name=_('Pick Col')), depends=['pick_id#layout_col'])
    def pick_col(self):
        try:
            return self.pick_id.layout_col
        except:
            return None

    @computed(models.PositiveSmallIntegerField(blank=True, null=True, verbose_name=_('Pick Row')), depends=['pick_id#layout_row'])
    def pick_row(self):
        try:
            return self.pick_id.layout_row
        except:
            return None

    @computed(models.PositiveSmallIntegerField(blank=True, null=True, verbose_name=_('Place Col')), depends=['place_id#layout_col'])
    def place_col(self):
        try:
            return self.place_id.layout_col
        except:
            return None

    @computed(models.PositiveSmallIntegerField(blank=True, null=True, verbose_name=_('Place Row')), depends=['place_id#layout_row'])
    def place_row(self):
        try:
            return self.place_id.layout_row
        except:
            return None

    def save(self, *args, **kwargs):
        if self.mode == 1:
            self.pick_id = None
        elif self.mode == 2:
            self.robot_no = None
        super().save(*args, **kwargs)

    def __str__(self):
        return '{}'.format(self.id)

    class Meta:
        # todo need to change to order storage first then retrieval
        ordering = ('id',)


class AgvTransfer(ComputedFieldsModel):
    run_choices = list(enumerate([_('Stop'), _('Start')]))
    run = models.PositiveSmallIntegerField(choices=run_choices, default=0)
    status_choices = list(enumerate([_('Wait for queue'), _('Sending command'), _('Operating queue')]))
    status = models.PositiveSmallIntegerField(choices=status_choices, default=1, verbose_name=_('AGV Status'))
    step_choices = [(i + 1, i + 1) for i in range(7)]
    step = models.PositiveSmallIntegerField(choices=step_choices, default=1)
    x_nav = models.FloatField(default=0.0)
    y_nav = models.FloatField(default=0.0)
    beta_nav = models.FloatField(default=0.0)
    pause_choices = list(enumerate([_('Not Pause'), _('Pause')]))
    pause = models.PositiveSmallIntegerField(choices=pause_choices, default=0)
    pattern_choices = [(0.0, 'P0: ArmRun -> Rev'), (1.0, 'P1: Rev -> ArmRun'), (2.0, 'P2: ArmPrepare -> FW -> Pick(Robot)'), (3.0, 'P3: ArmPrepare -> FW -> Pick(Storage)'), (4.0, 'P4: FW -> ArmPut')]
    pattern = models.FloatField(choices=pattern_choices, default=0.0)
    qty = models.FloatField(default=0.0)
    x1 = models.FloatField(default=0.0)
    y1 = models.FloatField(default=0.0)
    x2 = models.FloatField(default=0.0)
    y2 = models.FloatField(default=0.0)
    x3 = models.FloatField(default=0.0)
    y3 = models.FloatField(default=0.0)
    x4 = models.FloatField(default=0.0)
    y4 = models.FloatField(default=0.0)
    x5 = models.FloatField(default=0.0)
    y5 = models.FloatField(default=0.0)
    col1 = models.PositiveSmallIntegerField(default=0)
    row1 = models.PositiveSmallIntegerField(default=0)
    col2 = models.PositiveSmallIntegerField(default=0)
    row2 = models.PositiveSmallIntegerField(default=0)
    col3 = models.PositiveSmallIntegerField(default=0)
    row3 = models.PositiveSmallIntegerField(default=0)
    col4 = models.PositiveSmallIntegerField(default=0)
    row4 = models.PositiveSmallIntegerField(default=0)
    col5 = models.PositiveSmallIntegerField(default=0)
    row5 = models.PositiveSmallIntegerField(default=0)
    history = HistoricalRecords(excluded_fields=['x_nav', 'y_nav', 'beta_nav', 'x1', 'y1', 'x2', 'y2', 'x3', 'y3', 'x4', 'y4', 'x5', 'y5', 'col1', 'row1', 'col2', 'row2', 'col3', 'row3', 'col4', 'row4', 'col5', 'row5'])

    def __str__(self):
        return '{}'.format(self.id)

    class Meta:
        ordering = ('id',)
