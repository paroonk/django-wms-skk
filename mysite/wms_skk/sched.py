import numpy as np
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from django.db.models import Q
from django.dispatch import receiver
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_pandas.io import read_frame
from simple_history.signals import post_create_historical_record

from .models import *

transfer_hold = {
    1: 0,
}
x_check = 999.9
y_check = 999.9

db_update_list = []
db_update_initial = True


def datetime_now():
    return timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S   ')


def robot_check():
    qs_robot = RobotQueue.objects.filter(updated=1)
    if qs_robot:
        qs_plan = AgvProductionPlan.objects.all()
        if qs_plan:
            obj_robot = qs_robot.first()
            obj_plan = qs_plan.select_related('product_id').first()

            qs_avail_storage = Storage.objects.filter(storage_for=obj_plan.product_id.product_id, have_inventory=False).exclude(
                storage_id__in=AgvQueue1.objects.all().values('place_id'))

            avail_storage_zone_a = qs_avail_storage.filter(zone='A').order_by('area', 'col', 'row')
            avail_storage_zone_b = qs_avail_storage.filter(zone='B').order_by('-area', '-col', 'row')
            pk_avail_storage_list = list(avail_storage_zone_a.values_list('storage_id', flat=True)) + list(avail_storage_zone_b.values_list('storage_id', flat=True))
            # todo order by newest
            print(pk_avail_storage_list)

            if pk_avail_storage_list:
                obj_to = get_object_or_404(Storage, storage_id=pk_avail_storage_list[0])
                obj_queue = AgvQueue1()
                obj_queue.product_id = obj_plan.product_id
                obj_queue.lot_name = obj_plan.lot_name
                obj_queue.qty_act = obj_robot.qty_act
                obj_queue.created_on = timezone.now()
                obj_queue.robot_no = obj_robot.robot_no
                obj_queue.pick_id = None
                obj_queue.place_id = obj_to
                obj_queue.mode = 1
                obj_queue.updated = 0
                obj_queue.changeReason = 'Storage Order'
                obj_queue.save()

                obj_robot.changeReason = 'Move to AGV Queue'
                obj_robot.delete()

                obj_plan.qty_remain = obj_plan.qty_remain - obj_robot.qty_act
                if int(obj_plan.qty_remain) <= 0:
                    obj_plan.changeReason = 'Finish This Production Plan'
                    obj_plan.delete()
                else:
                    obj_plan.changeReason = 'Update For Storage Order'
                    obj_plan.save()


def transfer_check():
    if not AgvTransfer1.objects.filter(id=1).exists():
        qs_transfer1 = AgvTransfer1(id=1)
        qs_transfer1.save()

    qs_transfer1 = AgvTransfer1.objects.filter(id=1)
    qs_transfer_list = [qs_transfer1]

    for agv_no, qs_transfer in enumerate(qs_transfer_list, 1):
        obj_transfer = get_object_or_404(qs_transfer)
        if obj_transfer.status == 0:
            if agv_no == 1:
                qs_queue = AgvQueue1.objects.all()
            scheduler.add_job(agv_route, 'date', run_date=timezone.now(), args=[agv_no, qs_transfer, qs_queue], id='agv_route', replace_existing=True)


def transfer_adjust(obj_transfer):
    beta_offset = 2.505388716
    agv_beta = obj_transfer.beta_nav - beta_offset
    if agv_beta < 0:
        agv_beta = agv_beta + 360.0
    nav_offset = 0.5
    agv_x = obj_transfer.x_nav - (nav_offset * np.cos(agv_beta * np.pi / 180.0))
    agv_y = obj_transfer.y_nav - (nav_offset * np.sin(agv_beta * np.pi / 180.0))
    return agv_x, agv_y, agv_beta


def transfer_update(agv_no):
    if agv_no == 1:
        qs_transfer = AgvTransfer1.objects.filter(id=1)
        obj_transfer = get_object_or_404(qs_transfer)

    obj_transfer.status = 1
    obj_transfer.changeReason = 'Delayed AGV Command'
    obj_transfer.save()
    scheduler.add_job(transfer_reset_hold, 'date', run_date=timezone.now() + timezone.timedelta(seconds=10), args=[agv_no], id='transfer_reset_hold', replace_existing=True)
    print(datetime_now() + 'Send New Command to AGV')


def transfer_reset_hold(agv_no):
    global transfer_hold
    transfer_hold[agv_no] = 0


def agv_route(agv_no, qs_transfer, qs_queue):
    global transfer_hold, x_check, y_check

    obj_transfer = get_object_or_404(qs_transfer)
    agv_x, agv_y, agv_beta = transfer_adjust(obj_transfer)

    # Calculate Route
    # Pattern 0: ArmRun -> Rev
    # Pattern 1: Rev -> ArmRun
    # Pattern 2: ArmPrepare -> FW -> Pick(Robot)
    # Pattern 3: ArmPrepare -> FW -> Pick(Storage)
    # Pattern 4: FW -> ArmPut
    # Reverse NAV Offset 1.14m
    # Forward NAV Offset 0.60m + dist_Offset (Pattern 3,4)

    df_queue = read_frame(qs_queue, index_col='id', verbose=False)
    if len(df_queue) >= 1 and transfer_hold[agv_no] == 0:
        active_queue = df_queue.iloc[0]
        print('\n' + datetime_now() + 'Step = {}'.format(obj_transfer.step))

        robot_row = 6
        runway_row = 9

        # Check Distance
        dist_check = 2.0
        dist_error = np.sqrt((agv_x - x_check) ** 2 + (agv_y - y_check) ** 2)

        if active_queue['mode'] == 1:
            if obj_transfer.step == 1:
                target_col = 45 if active_queue['robot_no'] == 1 else 40
                target_row = runway_row
                if dist_error > dist_check:
                    route_calculate(agv_no, obj_transfer, 0, agv_x, agv_y, target_col, target_row)
                else:
                    print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check, y_check, dist_error))
                    x_check = y_check = 999.9
                    obj_transfer.step = obj_transfer.step + 1
                    obj_transfer.changeReason = 'Next Step'
                    obj_transfer.save()
            elif obj_transfer.step == 2:
                target_col = 45 if active_queue['robot_no'] == 1 else 40
                target_row = robot_row
                if dist_error > (dist_check + 2.0):
                    obj_coor = get_object_or_404(Coordinate, layout_col=target_col, layout_row=runway_row)
                    col_offset = 1 if (agv_x < obj_coor.coor_x) else -1
                    obj_coor = get_object_or_404(Coordinate, layout_col=target_col + col_offset, layout_row=runway_row)
                    fix_x = obj_coor.coor_x
                    fix_y = obj_coor.coor_y
                    route_calculate(agv_no, obj_transfer, 2, fix_x, fix_y, target_col, target_row)
                else:
                    print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check, y_check, dist_error))
                    x_check = y_check = 999.9
                    obj_transfer.step = obj_transfer.step + 1
                    obj_transfer.changeReason = 'Next Step'
                    obj_transfer.save()
            elif obj_transfer.step == 3:
                target_col = 45 if active_queue['robot_no'] == 1 else 40
                target_row = runway_row
                if dist_error > dist_check:
                    obj_coor = get_object_or_404(Coordinate, layout_col=target_col, layout_row=robot_row)
                    fix_x = obj_coor.coor_x
                    fix_y = obj_coor.coor_y
                    route_calculate(agv_no, obj_transfer, 1, fix_x, fix_y, target_col, target_row)
                else:
                    print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check, y_check, dist_error))
                    x_check = y_check = 999.9
                    obj_transfer.step = obj_transfer.step + 1
                    obj_transfer.changeReason = 'Next Step'
                    obj_transfer.save()
            elif obj_transfer.step == 4:
                target_col = active_queue['place_col']
                target_row = runway_row
                if dist_error > dist_check:
                    route_calculate(agv_no, obj_transfer, 0, agv_x, agv_y, target_col, target_row)
                else:
                    print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check, y_check, dist_error))
                    x_check = y_check = 999.9
                    obj_transfer.step = obj_transfer.step + 1
                    obj_transfer.changeReason = 'Next Step'
                    obj_transfer.save()
            elif obj_transfer.step == 5:
                target_col = active_queue['place_col']
                target_row = active_queue['place_row']
                if dist_error > dist_check:
                    obj_coor = get_object_or_404(Coordinate, layout_col=target_col, layout_row=runway_row)
                    col_offset = 1 if (agv_x < obj_coor.coor_x) else -1
                    obj_coor = get_object_or_404(Coordinate, layout_col=target_col + col_offset, layout_row=runway_row)
                    fix_x = obj_coor.coor_x
                    fix_y = obj_coor.coor_y
                    route_calculate(agv_no, obj_transfer, 4, fix_x, fix_y, target_col, target_row)
                else:
                    print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check, y_check, dist_error))
                    x_check = y_check = 999.9
                    obj_transfer.step = obj_transfer.step + 1
                    obj_transfer.changeReason = 'Next Step'
                    obj_transfer.save()
            elif obj_transfer.step == 6:
                target_col = active_queue['place_col']
                if active_queue['place_row'] > runway_row:
                    target_row = runway_row + 1 if active_queue['place_row'] - 2 > runway_row else runway_row
                elif active_queue['place_row'] < runway_row:
                    target_row = runway_row - 1 if active_queue['place_row'] + 2 < runway_row else runway_row
                if dist_error > dist_check:
                    obj_coor = get_object_or_404(Coordinate, layout_col=target_col, layout_row=active_queue['place_row'])
                    fix_x = obj_coor.coor_x
                    fix_y = obj_coor.coor_y
                    route_calculate(agv_no, obj_transfer, 1, fix_x, fix_y, target_col, target_row)
                else:
                    print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check, y_check, dist_error))
                    print(datetime_now() + 'Finish Order')
                    x_check = y_check = 999.9
                    obj_transfer.step = 1
                    obj_transfer.changeReason = 'Finish Order'
                    obj_transfer.save()

                    obj_storage = get_object_or_404(Storage, storage_id=active_queue['place_id'])
                    obj_storage.inv_product = get_object_or_404(Product, product_id=active_queue['product_id'])
                    obj_storage.inv_qty = active_queue['qty_act']
                    obj_storage.lot_name = active_queue['lot_name']
                    obj_storage.created_on = active_queue['created_on']
                    obj_storage.updated_on = timezone.now()
                    obj_storage.changeReason = 'Storage Order'
                    obj_storage.save()

                    obj_queue = get_object_or_404(qs_queue, place_id=active_queue['place_id'])
                    obj_queue.changeReason = 'Finish This AGV Queue'
                    obj_queue.delete()
            else:
                obj_transfer.step = 1
                obj_transfer.changeReason = 'Step Error, Reset To Step 1'
                obj_transfer.save()

        elif active_queue['mode'] == 2:
            if obj_transfer.step == 1:
                target_col = active_queue['pick_col']
                target_row = runway_row
                if dist_error > dist_check:
                    route_calculate(agv_no, obj_transfer, 0, agv_x, agv_y, target_col, target_row)
                else:
                    print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check, y_check, dist_error))
                    x_check = y_check = 999.9
                    obj_transfer.step = obj_transfer.step + 1
                    obj_transfer.changeReason = 'Next Step'
                    obj_transfer.save()
            elif obj_transfer.step == 2:
                target_col = active_queue['pick_col']
                target_row = active_queue['pick_row']
                if dist_error > dist_check:
                    obj_coor = get_object_or_404(Coordinate, layout_col=target_col, layout_row=runway_row)
                    col_offset = 1 if (agv_x < obj_coor.coor_x) else -1
                    obj_coor = get_object_or_404(Coordinate, layout_col=target_col + col_offset, layout_row=runway_row)
                    fix_x = obj_coor.coor_x
                    fix_y = obj_coor.coor_y
                    route_calculate(agv_no, obj_transfer, 3, fix_x, fix_y, target_col, target_row)
                else:
                    print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check, y_check, dist_error))
                    x_check = y_check = 999.9
                    obj_transfer.step = obj_transfer.step + 1
                    obj_transfer.changeReason = 'Next Step'
                    obj_transfer.save()
            elif obj_transfer.step == 3:
                target_col = active_queue['place_col']
                target_row = runway_row
                if dist_error > dist_check:
                    route_calculate(agv_no, obj_transfer, 0, agv_x, agv_y, target_col, target_row)
                else:
                    print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check, y_check, dist_error))
                    x_check = y_check = 999.9
                    obj_transfer.step = obj_transfer.step + 1
                    obj_transfer.changeReason = 'Next Step'
                    obj_transfer.save()
            elif obj_transfer.step == 4:
                target_col = active_queue['place_col']
                target_row = active_queue['place_row']
                if dist_error > dist_check:
                    obj_coor = get_object_or_404(Coordinate, layout_col=target_col, layout_row=runway_row)
                    col_offset = 1 if (agv_x < obj_coor.coor_x) else -1
                    obj_coor = get_object_or_404(Coordinate, layout_col=target_col + col_offset, layout_row=runway_row)
                    fix_x = obj_coor.coor_x
                    fix_y = obj_coor.coor_y
                    route_calculate(agv_no, obj_transfer, 4, fix_x, fix_y, target_col, target_row)
                else:
                    print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check, y_check, dist_error))
                    x_check = y_check = 999.9
                    obj_transfer.step = obj_transfer.step + 1
                    obj_transfer.changeReason = 'Next Step'
                    obj_transfer.save()
            elif obj_transfer.step == 5:
                target_col = active_queue['place_col']
                if active_queue['place_row'] > runway_row:
                    target_row = runway_row + 1 if active_queue['place_row'] - 2 > runway_row else runway_row
                elif active_queue['place_row'] < runway_row:
                    target_row = runway_row - 1 if active_queue['place_row'] + 2 < runway_row else runway_row
                if dist_error > dist_check:
                    obj_coor = get_object_or_404(Coordinate, layout_col=target_col, layout_row=active_queue['place_row'])
                    fix_x = obj_coor.coor_x
                    fix_y = obj_coor.coor_y
                    route_calculate(agv_no, obj_transfer, 1, fix_x, fix_y, target_col, target_row)
                else:
                    print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check, y_check, dist_error))
                    x_check = y_check = 999.9
                    obj_transfer.step = 1
                    obj_transfer.changeReason = 'Finish Order'
                    obj_transfer.save()

                    obj_storage = get_object_or_404(Storage, storage_id=active_queue['place_id'])
                    obj_storage.inv_product = get_object_or_404(Product, product_id=active_queue['product_id'])
                    obj_storage.inv_qty = active_queue['qty_act']
                    obj_storage.lot_name = active_queue['lot_name']
                    obj_storage.created_on = active_queue['created_on']
                    obj_storage.updated_on = timezone.now()
                    obj_storage.changeReason = 'Retrieve/Move Order'
                    obj_storage.save()

                    obj_storage = get_object_or_404(Storage, storage_id=active_queue['pick_id'])
                    obj_storage.inv_product = None
                    obj_storage.inv_qty = None
                    obj_storage.lot_name = None
                    obj_storage.created_on = None
                    obj_storage.updated_on = timezone.now()
                    obj_storage.changeReason = 'Retrieve/Move Order'
                    obj_storage.save()

                    obj_queue = get_object_or_404(qs_queue, place_id=active_queue['place_id'])
                    obj_queue.changeReason = 'Finish This AGV Queue'
                    obj_queue.delete()
            else:
                obj_transfer.step = 1
                obj_transfer.changeReason = 'Step Error, Reset To Step 1'
                obj_transfer.save()
                print('Step Error, Reset To Step 1')


def position_cal(agv_x, agv_y):
    df_route = pd.DataFrame()
    df_coordinate = read_frame(Coordinate.objects.all(), index_col='coor_id', verbose=False)
    df_coordinate['dist'] = np.sqrt((agv_x - df_coordinate['coor_x']) ** 2 + (agv_y - df_coordinate['coor_y']) ** 2)
    index = df_coordinate.nsmallest(1, 'dist', keep='first').index.values
    df_coordinate.drop('dist', 1, inplace=True)
    df_route = df_route.append(df_coordinate.loc[index], sort=False)
    agv_col, agv_row, x, y = df_route.iloc[-1]
    return agv_col, agv_row


def dist_compensate(x1, y1, x2, y2, dist_offset):
    theta = None
    dx = x2 - x1
    dy = y2 - y1
    dist = np.sqrt(dx ** 2 + dy ** 2)
    if dx != 0:
        theta = np.arctan(dy / dx)
    elif dx == 0 and dy >= 0:
        theta = np.pi / 2
    elif dx == 0 and dy < 0:
        theta = 3 * np.pi / 2
    if dx >= 0 and dy >= 0:
        theta = theta
    elif dx < 0 and dy >= 0:
        theta = theta + np.pi
    elif dx < 0 and dy < 0:
        theta = theta + np.pi
    elif dx >= 0 and dy < 0:
        theta = theta + 2 * np.pi
    x_offset = x1 + (dist + dist_offset) * np.cos(theta)
    y_offset = y1 + (dist + dist_offset) * np.sin(theta)
    return x_offset, y_offset


def route_calculate(agv_no, obj_transfer, pattern, agv_x, agv_y, target_col, target_row):
    global transfer_hold, x_check, y_check

    print(datetime_now() + 'Recalculate Route for AGV')
    agv_col, agv_row = position_cal(agv_x, agv_y)
    if agv_col == target_col and agv_row == target_row:
        obj_coor = get_object_or_404(Coordinate, layout_col=agv_col, layout_row=agv_row)
        x_check = obj_coor.coor_x
        y_check = obj_coor.coor_y
    else:
        runway_row = 9

        # Calculate Route Coordinate
        df_route = pd.DataFrame()
        new_coor = read_frame(Coordinate.objects.filter(layout_col=agv_col, layout_row=agv_row), index_col='coor_id', verbose=False)
        df_route = df_route.append(new_coor)
        while (agv_col != target_col) or (agv_row != target_row):
            if agv_col != target_col and agv_row != runway_row:
                new_coor = read_frame(Coordinate.objects.filter(layout_col=agv_col, layout_row=runway_row), index_col='coor_id', verbose=False)
                df_route = df_route.append(new_coor)
            elif agv_col != target_col and agv_row == runway_row:
                new_coor = read_frame(Coordinate.objects.filter(layout_col=target_col, layout_row=runway_row), index_col='coor_id', verbose=False)
                df_route = df_route.append(new_coor)
            elif agv_col == target_col:
                new_coor = read_frame(Coordinate.objects.filter(layout_col=target_col, layout_row=target_row), index_col='coor_id', verbose=False)
                df_route = df_route.append(new_coor)
            agv_col, agv_row, x, y = df_route.iloc[-1]

        # Start point offset #
        dist_offset_start = 0.1
        df_route.iloc[0, df_route.columns.get_loc('coor_x')], df_route.iloc[0, df_route.columns.get_loc('coor_y')] = \
            dist_compensate(df_route['coor_x'].iloc[1], df_route['coor_y'].iloc[1], df_route['coor_x'].iloc[0], df_route['coor_y'].iloc[0], dist_offset_start)

        # Final point offset #
        dist_offset_final = 1.33
        dist_offset = {
            0: dist_offset_final + 1.3,
            1: dist_offset_final - 0.6,
            2: dist_offset_final,
            3: dist_offset_final,
            4: dist_offset_final,
        }

        df_route.iloc[-1, df_route.columns.get_loc('coor_x')], df_route.iloc[-1, df_route.columns.get_loc('coor_y')] = \
            dist_compensate(df_route['coor_x'].iloc[-2], df_route['coor_y'].iloc[-2], df_route['coor_x'].iloc[-1], df_route['coor_y'].iloc[-1], dist_offset[pattern])
        df_route.reset_index(drop=True, inplace=True)

        x_check, y_check = dist_compensate(df_route['coor_x'].iloc[-2], df_route['coor_y'].iloc[-2], df_route['coor_x'].iloc[-1], df_route['coor_y'].iloc[-1], -dist_offset_final)

        print(' Pattern = {}'.format(pattern))
        print(df_route.to_string(index=False))
        print(' Target x = {:.6f}, y = {:.6f}'.format(x_check, y_check))

        obj_transfer.pattern = float(pattern)
        obj_transfer.qty = float(len(df_route))
        obj_transfer.x1 = df_route['coor_x'].iloc[0] if len(df_route) > 0 else 0
        obj_transfer.x2 = df_route['coor_x'].iloc[1] if len(df_route) > 1 else 0
        obj_transfer.x3 = df_route['coor_x'].iloc[2] if len(df_route) > 2 else 0
        obj_transfer.x4 = df_route['coor_x'].iloc[3] if len(df_route) > 3 else 0
        obj_transfer.x5 = df_route['coor_x'].iloc[4] if len(df_route) > 4 else 0
        obj_transfer.y1 = df_route['coor_y'].iloc[0] if len(df_route) > 0 else 0
        obj_transfer.y2 = df_route['coor_y'].iloc[1] if len(df_route) > 1 else 0
        obj_transfer.y3 = df_route['coor_y'].iloc[2] if len(df_route) > 2 else 0
        obj_transfer.y4 = df_route['coor_y'].iloc[3] if len(df_route) > 3 else 0
        obj_transfer.y5 = df_route['coor_y'].iloc[4] if len(df_route) > 4 else 0
        obj_transfer.changeReason = 'AGV Update Pattern and Coordinate'
        obj_transfer.save()
        transfer_hold[agv_no] = 1
        scheduler.add_job(transfer_update, 'date', run_date=timezone.now() + timezone.timedelta(seconds=3), args=[agv_no], id='transfer_update', replace_existing=True)


def update_product_db():
    global db_update_list, db_update_initial
    if len(db_update_list) > 0:
        for product_id in db_update_list:
            if len(Product.objects.filter(product_id=product_id)) == 1:
                obj = get_object_or_404(Product, product_id=product_id)

                storage_count = Storage.objects.filter(storage_for=obj.product_id).count()
                obj.qty_storage = storage_count * obj.qty_limit

                inv = Storage.objects.filter(storage_for=obj.product_id, inv_product=obj.product_id).aggregate(models.Sum('inv_qty'))['inv_qty__sum']
                obj.qty_inventory = inv if inv else 0

                buffer = Storage.objects.filter(is_inventory=False, inv_product=obj.product_id).aggregate(models.Sum('inv_qty'))['inv_qty__sum']
                obj.qty_buffer = buffer if buffer else 0

                misplace = Storage.objects.filter(is_inventory=True, inv_product=obj.product_id).exclude(storage_for=obj.product_id).aggregate(models.Sum('inv_qty'))[
                    'inv_qty__sum']
                obj.qty_misplace = misplace if misplace else 0

                obj.qty_total = obj.qty_inventory + obj.qty_buffer + obj.qty_misplace

                storage_plan = AgvProductionPlan.objects.filter(product_id__product_id=obj.product_id).aggregate(models.Sum('qty_remain'))['qty_remain__sum']
                storage_plan = storage_plan if storage_plan else 0
                queue_to_storage = AgvQueue1.objects.filter(
                    place_id__storage_id__in=Storage.objects.filter(storage_for=obj.product_id).values('storage_id')
                ).aggregate(models.Sum('qty_act'))['qty_act__sum']
                queue_to_storage = queue_to_storage if queue_to_storage else 0
                obj.qty_storage_avail = obj.qty_storage - obj.qty_inventory - storage_plan - queue_to_storage

                qs_avail_inventory = Storage.objects.filter(inv_product=obj.product_id, storage_for=obj.product_id).exclude(
                    storage_id__in=AgvQueue1.objects.filter(mode=2).values('pick_id'))
                qs_mismatch = Storage.objects.filter(~Q(inv_product=obj.product_id), storage_for=obj.product_id, have_inventory=True).exclude(
                    storage_id__in=AgvQueue1.objects.filter(mode=2).values('pick_id'))
                for column_id in qs_mismatch.order_by().distinct().values_list('column_id', flat=True):
                    mismatch_outer = qs_mismatch.filter(column_id=column_id).order_by('row').last().row
                    if mismatch_outer:
                        qs_avail_inventory = qs_avail_inventory.exclude(column_id=column_id, row__lt=mismatch_outer)
                qty_avail_inventory = qs_avail_inventory.aggregate(models.Sum('inv_qty'))['inv_qty__sum']
                obj.qty_inventory_avail = qty_avail_inventory if qty_avail_inventory else 0

                if db_update_initial:
                    obj.save_without_historical_record()
                else:
                    obj.changeReason = 'Update Quantity'
                    obj.save()

                db_update_list.remove(product_id)
            if len(db_update_list) > 0:
                update_product_db()
            if db_update_initial:
                db_update_initial = False


@receiver(post_create_historical_record, sender=HistoricalStorage, dispatch_uid="post_update_storage_db")
def post_update_storage_db(sender, instance, **kwargs):
    global db_update_list
    new_record = instance.history.first()
    try:
        old_record = new_record.prev_record
    except:
        old_record = None
    if old_record:
        new_obj, old_obj = new_record.instance, old_record.instance
        delta = new_record.diff_against(old_record)
        for change in delta.changes:
            if change.field == 'storage_for':
                if old_obj.is_inventory:
                    db_update_list.append(change.old) if change.old not in db_update_list else db_update_list
                if new_obj.is_inventory:
                    db_update_list.append(change.new) if change.new not in db_update_list else db_update_list
            elif change.field == 'inv_product':
                if new_obj.inv_product:
                    db_update_list.append(new_obj.inv_product.product_id) if new_obj.inv_product.product_id not in db_update_list else db_update_list
                try:
                    if old_obj.inv_product:
                        db_update_list.append(old_obj.inv_product.product_id) if old_obj.inv_product.product_id not in db_update_list else db_update_list
                except Product.DoesNotExist:
                    pass
            elif change.field == 'inv_qty':
                if new_obj.inv_product:
                    db_update_list.append(new_obj.inv_product.product_id) if new_obj.inv_product.product_id not in db_update_list else db_update_list
        scheduler.add_job(update_product_db, 'date', run_date=timezone.now() + timezone.timedelta(seconds=1), id='update_product_db', replace_existing=True)


def agv_dummy():
    qs_transfer = AgvTransfer1.objects.filter(id=1)
    obj_transfer = get_object_or_404(qs_transfer)
    obj_transfer.x_nav -= 1
    if obj_transfer.x_nav <= -61:
        obj_transfer.x_nav = 31
    obj_transfer.changeReason = 'Simulate AGV Moving'
    obj_transfer.save()


scheduler = BackgroundScheduler()
scheduler.add_job(transfer_check, 'interval', seconds=1, id='transfer_check', replace_existing=True)
scheduler.add_job(robot_check, 'interval', seconds=1, id='robot_check', replace_existing=True)
# scheduler.add_job(agv_dummy, 'interval', seconds=1, id='agv_dummy', replace_existing=True)

print(datetime_now() + 'Program Started')
db_update_list = list(Product.objects.all().values_list('product_id', flat=True))
update_product_db()
