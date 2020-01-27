import numpy as np
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from django.db.models import Q
from django.db.utils import ProgrammingError
from django.dispatch import receiver
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_pandas.io import read_frame
from simple_history.signals import post_create_historical_record

from .models import *

agv_list = [1, 2]
robot_list = [1, 2]

transfer_hold = {}
x_check = {}
y_check = {}
for i in agv_list:
    transfer_hold[i] = 0
    x_check[i] = 999.9
    y_check[i] = 999.9

db_update_list = []
db_update_initial = True

# Home Location #
home_col = 48
home_row = 9


def datetime_now():
    return timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S   ')


def initial_data():
    try:
        # Create buffer sql variable for communication #
        for agv_no in agv_list:
            if not AgvTransfer.objects.filter(id=agv_no).exists():
                qs_transfer = AgvTransfer(id=agv_no)
                qs_transfer.save()

        for robot_no in robot_list:
            if not RobotStatus.objects.filter(robot_no=robot_no).exists():
                qs_robot = RobotStatus(robot_no=robot_no)
                qs_robot.save()

        # Clear old log #
        days_history_keep = 30
        date_keep = timezone.now() - timezone.timedelta(days=days_history_keep)
        # Product.history.filter(history_date__lt=date_keep).delete()
        # Storage.history.filter(history_date__lt=date_keep).delete()
        AgvProductionPlan.history.filter(history_date__lt=date_keep).delete()
        RobotQueue.history.filter(history_date__lt=date_keep).delete()
        AgvQueue.history.filter(history_date__lt=date_keep).delete()
        AgvTransfer.history.filter(history_date__lt=date_keep).delete()

    except ProgrammingError:
        pass


def robot_check():
    try:
        qs_robot = RobotQueue.objects.filter(updated=1)
        if qs_robot:
            qs_plan = AgvProductionPlan.objects.all()
            if qs_plan:
                class Found(Exception):
                    pass

                try:
                    scheduler.pause_job(job_id='robot_check')
                    for i in qs_plan.select_related('product_name'):
                        for j in qs_robot:
                            if i.product_name.product_name == j.get_product_id_display():
                                raise Found
                except Found:
                    obj_plan = i
                    obj_robot = j

                    # Only store to pre-assigned storage and don't have any inventory before it #
                    qs_avail_storage = Storage.objects.filter(storage_for=obj_plan.product_name.product_name)
                    qs_occupied = qs_avail_storage.filter(Q(have_inventory=True) | Q(storage_id__in=AgvQueue.objects.all().values('place_id')))
                    for column_id in qs_occupied.order_by().distinct().values_list('column_id', flat=True):
                        occupied_outer = qs_occupied.filter(column_id=column_id).order_by('row').last()
                        if occupied_outer:
                            qs_avail_storage = qs_avail_storage.exclude(column_id=column_id, row__lte=occupied_outer.row)

                    pk_avail_storage_list = list(qs_avail_storage.order_by('col', 'row').values_list('storage_id', flat=True))
                    if pk_avail_storage_list:
                        # Find last storage column for obj_to
                        column_id_list = list(Storage.objects.filter(storage_for=obj_plan.product_name.product_name).order_by('col').distinct().values_list('column_id', flat=True))
                        df_created_on = pd.DataFrame(columns=['column_id', 'created_on']).set_index('column_id')
                        for column_id in column_id_list:
                            qs_last_inventory_in_column = Storage.objects.filter(column_id=column_id, have_inventory=True)
                            if qs_last_inventory_in_column.exists():
                                last_inventory_in_column = qs_last_inventory_in_column.order_by('-row')[0]
                                df_created_on.loc[column_id] = [last_inventory_in_column.created_on]
                        if len(df_created_on) > 0:
                            last_column_id = list(df_created_on.sort_values(by=['created_on'], ascending=False).index)[0]
                            last_column_id_index = column_id_list.index(last_column_id)
                            column_id_list = column_id_list[last_column_id_index:] + column_id_list[:last_column_id_index]
                            for column_id in column_id_list:
                                if Storage.objects.filter(storage_id__in=pk_avail_storage_list, column_id=column_id).exists():
                                    obj_to = Storage.objects.filter(storage_id__in=pk_avail_storage_list, column_id=column_id).order_by('row').first()
                                    break
                                # Find next available column for obj_to if last storage column is full
                        else:
                            obj_to = Storage.objects.filter(storage_id=pk_avail_storage_list[0]).first()

                        obj_queue = AgvQueue()
                        obj_queue.product_name = obj_plan.product_name
                        obj_queue.lot_name = obj_plan.lot_name
                        obj_queue.qty_act = obj_robot.qty_act
                        obj_queue.created_on = timezone.now()
                        obj_queue.robot_no = obj_robot.robot_no
                        obj_queue.pick_id = None
                        obj_queue.place_id = obj_to
                        obj_queue.mode = 1
                        obj_queue.updated = 0
                        obj_queue.changeReason = 'New AGV Queue'
                        obj_queue.save()

                        obj_robot.changeReason = 'Update Robot Queue (Move to transfer)'
                        obj_robot.delete()

                        obj_plan.qty_remain = obj_plan.qty_remain - obj_robot.qty_act
                        if int(obj_plan.qty_remain) <= 0:
                            obj_plan.qty_remain = 0
                            obj_plan.changeReason = 'Finish Production Plan'
                            obj_plan.delete()
                        else:
                            obj_plan.changeReason = 'Update Production Plan (Move to queue)'
                            obj_plan.save()
                finally:
                    scheduler.resume_job(job_id='robot_check')
    except ProgrammingError:
        pass


def transfer_check():
    global x_check, y_check
    try:
        for agv_no in agv_list:
            if AgvTransfer.objects.filter(id=agv_no).exists():
                qs_transfer1 = AgvTransfer.objects.filter(id=agv_no)
                qs_transfer_list = [qs_transfer1]

        for agv_no, qs_transfer in enumerate(qs_transfer_list, 1):
            try:
                obj_transfer = get_object_or_404(qs_transfer)
                if obj_transfer.run == 1 and obj_transfer.status == 0:
                    if agv_no == 1:
                        qs_queue = AgvQueue.objects.all()
                        scheduler.add_job(agv_route, 'date', run_date=timezone.now(), args=[agv_no, qs_transfer, qs_queue], id='agv_route', replace_existing=True)
                elif obj_transfer.run == 0:
                    x_check[agv_no] = y_check[agv_no] = 999.9
            except AgvTransfer.DoesNotExist:
                pass

    except ProgrammingError:
        pass


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
    qs_transfer = AgvTransfer.objects.filter(id=agv_no)
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
    global transfer_hold, x_check, y_check, home_col, home_row

    scheduler.pause_job(job_id='transfer_check')

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
        dist_error = np.sqrt((agv_x - x_check[agv_no]) ** 2 + (agv_y - y_check[agv_no]) ** 2)

        if obj_transfer.step == 1:
            if active_queue['mode'] == 1:
                target_col = 45 if active_queue['robot_no'] == 1 else 40
                target_row = runway_row
                if dist_error > dist_check:
                    route_calculate(agv_no, obj_transfer, 0, agv_x, agv_y, target_col, target_row)
                else:
                    print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check[agv_no], y_check[agv_no], dist_error))
                    x_check[agv_no] = y_check[agv_no] = 999.9
                    obj_transfer.step = obj_transfer.step + 1
                    obj_transfer.changeReason = 'Next Step'
                    obj_transfer.save()
            elif active_queue['mode'] == 2:
                target_col = active_queue['pick_col']
                target_row = runway_row
                if dist_error > dist_check:
                    route_calculate(agv_no, obj_transfer, 0, agv_x, agv_y, target_col, target_row)
                else:
                    print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check[agv_no], y_check[agv_no], dist_error))
                    x_check[agv_no] = y_check[agv_no] = 999.9
                    obj_transfer.step = obj_transfer.step + 1
                    obj_transfer.changeReason = 'Next Step'
                    obj_transfer.save()
        elif obj_transfer.step == 2:
            if active_queue['mode'] == 1:
                target_col = 45 if active_queue['robot_no'] == 1 else 40
                target_row = robot_row
                if dist_error > (dist_check + 3.0):
                    obj_coor = get_object_or_404(Coordinate, layout_col=target_col, layout_row=runway_row)
                    col_offset = 1 if (agv_x < obj_coor.coor_x) else -1
                    obj_coor = get_object_or_404(Coordinate, layout_col=target_col + col_offset, layout_row=runway_row)
                    fix_x = obj_coor.coor_x
                    fix_y = obj_coor.coor_y
                    route_calculate(agv_no, obj_transfer, 2, fix_x, fix_y, target_col, target_row)
                else:
                    print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check[agv_no], y_check[agv_no], dist_error))
                    x_check[agv_no] = y_check[agv_no] = 999.9
                    obj_transfer.step = obj_transfer.step + 1
                    obj_transfer.changeReason = 'Next Step'
                    obj_transfer.save()
            elif active_queue['mode'] == 2:
                target_col = active_queue['pick_col']
                target_row = active_queue['pick_row']
                if dist_error > (dist_check + 3.0):
                    obj_coor = get_object_or_404(Coordinate, layout_col=target_col, layout_row=runway_row)
                    col_offset = 1 if (agv_x < obj_coor.coor_x) else -1
                    obj_coor = get_object_or_404(Coordinate, layout_col=target_col + col_offset, layout_row=runway_row)
                    fix_x = obj_coor.coor_x
                    fix_y = obj_coor.coor_y
                    route_calculate(agv_no, obj_transfer, 3, fix_x, fix_y, target_col, target_row)
                else:
                    print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check[agv_no], y_check[agv_no], dist_error))
                    x_check[agv_no] = y_check[agv_no] = 999.9
                    obj_transfer.step = obj_transfer.step + 1
                    obj_transfer.changeReason = 'Next Step'
                    obj_transfer.save()
        elif obj_transfer.step == 3:
            if active_queue['mode'] == 1:
                target_col = 45 if active_queue['robot_no'] == 1 else 40
                target_row = runway_row
                if dist_error > dist_check:
                    obj_coor = get_object_or_404(Coordinate, layout_col=target_col, layout_row=robot_row)
                    fix_x = obj_coor.coor_x
                    fix_y = obj_coor.coor_y
                    route_calculate(agv_no, obj_transfer, 1, fix_x, fix_y, target_col, target_row)
                else:
                    print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check[agv_no], y_check[agv_no], dist_error))
                    x_check[agv_no] = y_check[agv_no] = 999.9
                    obj_transfer.step = obj_transfer.step + 1
                    obj_transfer.changeReason = 'Next Step'
                    obj_transfer.save()
            elif active_queue['mode'] == 2:
                target_col = active_queue['pick_col']
                target_row = runway_row
                if dist_error > dist_check:
                    obj_coor = get_object_or_404(Coordinate, layout_col=target_col, layout_row=active_queue['pick_row'])
                    fix_x = obj_coor.coor_x
                    fix_y = obj_coor.coor_y
                    route_calculate(agv_no, obj_transfer, 1, fix_x, fix_y, target_col, target_row)
                else:
                    print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check[agv_no], y_check[agv_no], dist_error))
                    x_check[agv_no] = y_check[agv_no] = 999.9
                    obj_transfer.step = obj_transfer.step + 1
                    obj_transfer.changeReason = 'Next Step'
                    obj_transfer.save()
        elif obj_transfer.step == 4:
            target_col = active_queue['place_col']
            target_row = runway_row
            if dist_error > dist_check:
                route_calculate(agv_no, obj_transfer, 0, agv_x, agv_y, target_col, target_row)
            else:
                print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check[agv_no], y_check[agv_no], dist_error))
                x_check[agv_no] = y_check[agv_no] = 999.9
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
                print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check[agv_no], y_check[agv_no], dist_error))
                x_check[agv_no] = y_check[agv_no] = 999.9
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
                print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check[agv_no], y_check[agv_no], dist_error))
                x_check[agv_no] = y_check[agv_no] = 999.9
                if target_row == runway_row:
                    obj_transfer.step = obj_transfer.step + 1
                    obj_transfer.changeReason = 'Next Step'
                    obj_transfer.save()
                else:
                    print(datetime_now() + 'Finish Order')
                    obj_transfer.step = 1
                    obj_transfer.changeReason = 'Finish Order'
                    obj_transfer.save()

                    if active_queue['mode'] == 1:
                        obj_storage = get_object_or_404(Storage, storage_id=active_queue['place_id'])
                        obj_storage.inv_product = get_object_or_404(Product, product_name=active_queue['product_name'])
                        obj_storage.inv_qty = active_queue['qty_act']
                        obj_storage.lot_name = active_queue['lot_name']
                        obj_storage.created_on = active_queue['created_on']
                        obj_storage.updated_on = timezone.now()
                        obj_storage.changeReason = 'New inventory (Storage Order)'
                        obj_storage.save()

                        obj_queue = get_object_or_404(qs_queue, place_id=active_queue['place_id'])
                        obj_queue.changeReason = 'Finish AGV Queue'
                        obj_queue.delete()
                    elif active_queue['mode'] == 2:
                        obj_storage = get_object_or_404(Storage, storage_id=active_queue['place_id'])
                        obj_storage.inv_product = get_object_or_404(Product, product_name=active_queue['product_name'])
                        obj_storage.inv_qty = active_queue['qty_act']
                        obj_storage.lot_name = active_queue['lot_name']
                        obj_storage.created_on = active_queue['created_on']
                        obj_storage.updated_on = timezone.now()
                        obj_storage.changeReason = 'New inventory (Retrieve/Move Order)'
                        obj_storage.save()

                        obj_storage = get_object_or_404(Storage, storage_id=active_queue['pick_id'])
                        obj_storage.inv_product = None
                        obj_storage.inv_qty = None
                        obj_storage.lot_name = None
                        obj_storage.created_on = None
                        obj_storage.updated_on = timezone.now()
                        obj_storage.changeReason = 'Remove inventory (Retrieve/Move Order)'
                        obj_storage.save()

                        obj_queue = get_object_or_404(qs_queue, place_id=active_queue['place_id'])
                        obj_queue.changeReason = 'Finish AGV Queue'
                        obj_queue.delete()
        elif obj_transfer.step == 7:
            target_col = home_col
            target_row = home_row
            if dist_error > dist_check:
                route_calculate(agv_no, obj_transfer, 0, agv_x, agv_y, target_col, target_row)
            else:
                print(datetime_now() + 'Finish, NAV {:.2f},{:.2f} Check {:.2f},{:.2f} Error {:.4f}'.format(agv_x, agv_y, x_check[agv_no], y_check[agv_no], dist_error))
                print(datetime_now() + 'Finish Order')
                x_check[agv_no] = y_check[agv_no] = 999.9
                obj_transfer.step = 1
                obj_transfer.changeReason = 'Finish Order'
                obj_transfer.save()

                if active_queue['mode'] == 1:
                    obj_storage = get_object_or_404(Storage, storage_id=active_queue['place_id'])
                    obj_storage.inv_product = get_object_or_404(Product, product_name=active_queue['product_name'])
                    obj_storage.inv_qty = active_queue['qty_act']
                    obj_storage.lot_name = active_queue['lot_name']
                    obj_storage.created_on = active_queue['created_on']
                    obj_storage.updated_on = timezone.now()
                    obj_storage.changeReason = 'New inventory (Storage Order)'
                    obj_storage.save()

                    obj_queue = get_object_or_404(qs_queue, place_id=active_queue['place_id'])
                    obj_queue.changeReason = 'Finish AGV Queue'
                    obj_queue.delete()
                elif active_queue['mode'] == 2:
                    obj_storage = get_object_or_404(Storage, storage_id=active_queue['place_id'])
                    obj_storage.inv_product = get_object_or_404(Product, product_name=active_queue['product_name'])
                    obj_storage.inv_qty = active_queue['qty_act']
                    obj_storage.lot_name = active_queue['lot_name']
                    obj_storage.created_on = active_queue['created_on']
                    obj_storage.updated_on = timezone.now()
                    obj_storage.changeReason = 'New inventory (Retrieve/Move Order)'
                    obj_storage.save()

                    obj_storage = get_object_or_404(Storage, storage_id=active_queue['pick_id'])
                    obj_storage.inv_product = None
                    obj_storage.inv_qty = None
                    obj_storage.lot_name = None
                    obj_storage.created_on = None
                    obj_storage.updated_on = timezone.now()
                    obj_storage.changeReason = 'Remove inventory (Retrieve/Move Order)'
                    obj_storage.save()

                    obj_queue = get_object_or_404(qs_queue, place_id=active_queue['place_id'])
                    obj_queue.changeReason = 'Finish AGV Queue'
                    obj_queue.delete()
        else:
            print('Step Error, Reset To Step 1')
            obj_transfer.step = 1
            obj_transfer.changeReason = 'Step Error, Reset To Step 1'
            obj_transfer.save()

    scheduler.resume_job(job_id='transfer_check')


def agv_route_home(agv_no, qs_transfer):
    global x_check, y_check, home_col, home_row

    scheduler.pause_job(job_id='transfer_check')

    obj_transfer = get_object_or_404(qs_transfer)
    pattern = 1.0
    agv_x, agv_y, agv_beta = transfer_adjust(obj_transfer)
    agv_col, agv_row = position_cal(agv_x, agv_y)
    target_col = home_col
    target_row = home_row

    if agv_row != target_row or agv_col != target_col:
        route_calculate(agv_no, obj_transfer, pattern, agv_x, agv_y, target_col, target_row)

        obj_transfer = get_object_or_404(qs_transfer)
        x_check[agv_no] = y_check[agv_no] = 999.9
        obj_transfer.step = 1
        obj_transfer.changeReason = 'Manual Update AGV Transfer'
        obj_transfer.save()

    scheduler.resume_job(job_id='transfer_check')


def agv_route_manual(agv_no, qs_transfer, pattern, target_col, target_row):
    global x_check, y_check

    scheduler.pause_job(job_id='transfer_check')

    obj_transfer = get_object_or_404(qs_transfer)
    agv_x, agv_y, agv_beta = transfer_adjust(obj_transfer)

    route_calculate(agv_no, obj_transfer, pattern, agv_x, agv_y, target_col, target_row)

    obj_transfer = get_object_or_404(qs_transfer)
    x_check[agv_no] = y_check[agv_no] = 999.9
    obj_transfer.step = 1
    obj_transfer.changeReason = 'Manual Update AGV Transfer'
    obj_transfer.save()

    scheduler.resume_job(job_id='transfer_check')


def position_cal(agv_x, agv_y):
    df_route = pd.DataFrame()
    df_coordinate = read_frame(Coordinate.objects.all(), index_col='coor_id', verbose=False)
    df_coordinate['dist'] = np.sqrt((agv_x - df_coordinate['coor_x']) ** 2 + (agv_y - df_coordinate['coor_y']) ** 2)
    try:
        index = df_coordinate.nsmallest(1, 'dist', keep='first').index.values
        df_coordinate.drop('dist', 1, inplace=True)
        df_route = df_route.append(df_coordinate.loc[index], sort=False)
        agv_col, agv_row, x, y = df_route.iloc[-1]
        return agv_col, agv_row
    except TypeError:
        return None, None


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
        x_check[agv_no] = obj_coor.coor_x
        y_check[agv_no] = obj_coor.coor_y
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
        df_route.iloc[0, df_route.columns.get_loc('coor_x')], df_route.iloc[0, df_route.columns.get_loc('coor_y')] = dist_compensate(
            df_route['coor_x'].iloc[1], df_route['coor_y'].iloc[1], df_route['coor_x'].iloc[0], df_route['coor_y'].iloc[0], dist_offset_start
        )

        # Final point offset #
        dist_offset_final = 1.33
        dist_offset = {
            0: dist_offset_final + 1.3,
            1: dist_offset_final - 0.6,
            2: dist_offset_final,
            3: dist_offset_final,
            4: dist_offset_final,
        }

        df_route.iloc[-1, df_route.columns.get_loc('coor_x')], df_route.iloc[-1, df_route.columns.get_loc('coor_y')] = dist_compensate(
            df_route['coor_x'].iloc[-2], df_route['coor_y'].iloc[-2], df_route['coor_x'].iloc[-1], df_route['coor_y'].iloc[-1], dist_offset[pattern]
        )
        df_route.reset_index(drop=True, inplace=True)

        x_check[agv_no], y_check[agv_no] = dist_compensate(df_route['coor_x'].iloc[-2], df_route['coor_y'].iloc[-2], df_route['coor_x'].iloc[-1], df_route['coor_y'].iloc[-1], -dist_offset_final)

        print(' Pattern = {}'.format(pattern))
        print(df_route.to_string(index=False))
        print(' Target x = {:.6f}, y = {:.6f}'.format(x_check[agv_no], y_check[agv_no]))

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
        for product_name in db_update_list:
            qs_product = Product.objects.filter(product_name=product_name)
            if qs_product.exists():
                obj = get_object_or_404(qs_product)

                storage_count = Storage.objects.filter(storage_for=obj.product_name).count()
                obj.qty_storage = storage_count * obj.qty_limit

                inv = Storage.objects.filter(storage_for=obj.product_name, inv_product=obj.product_name).aggregate(models.Sum('inv_qty'))['inv_qty__sum']
                obj.qty_inventory = inv if inv else 0

                buffer = Storage.objects.filter(is_inventory=False, inv_product=obj.product_name).aggregate(models.Sum('inv_qty'))['inv_qty__sum']
                obj.qty_buffer = buffer if buffer else 0

                misplace = Storage.objects.filter(is_inventory=True, inv_product=obj.product_name).exclude(storage_for=obj.product_name).aggregate(models.Sum('inv_qty'))['inv_qty__sum']
                obj.qty_misplace = misplace if misplace else 0

                obj.qty_total = obj.qty_inventory + obj.qty_buffer + obj.qty_misplace

                storage_plan = AgvProductionPlan.objects.filter(product_name__product_name=obj.product_name).aggregate(models.Sum('qty_remain'))['qty_remain__sum']
                storage_plan = storage_plan if storage_plan else 0
                qs_avail_storage = Storage.objects.filter(storage_for=obj.product_name)
                qs_occupied = qs_avail_storage.filter(Q(have_inventory=True) | Q(storage_id__in=AgvQueue.objects.all().values('place_id')))
                for column_id in qs_occupied.order_by().distinct().values_list('column_id', flat=True):
                    occupied_outer = qs_occupied.filter(column_id=column_id).order_by('row').last()
                    if occupied_outer:
                        qs_avail_storage = qs_avail_storage.exclude(column_id=column_id, row__lte=occupied_outer.row)
                obj.qty_storage_avail = (qs_avail_storage.count() * obj.qty_limit) - storage_plan

                qs_avail_inventory = Storage.objects.filter(inv_product=obj.product_name, storage_for=obj.product_name).exclude(storage_id__in=AgvQueue.objects.filter(mode=2).values('pick_id'))
                condition_misplace = ~Q(inv_product=obj.product_name) & Q(storage_for=obj.product_name) & Q(have_inventory=True)
                condition_new = Q(have_inventory=True) & Q(created_on__gte=timezone.now() - timezone.timedelta(days=7))
                qs_exclude = Storage.objects.filter(condition_misplace | condition_new)
                for column_id in qs_exclude.order_by().distinct().values_list('column_id', flat=True):
                    exclude_outer = qs_exclude.filter(column_id=column_id).order_by('row').last()
                    if exclude_outer:
                        qs_avail_inventory = qs_avail_inventory.exclude(column_id=column_id, row__lte=exclude_outer.row)
                qty_avail_inventory = qs_avail_inventory.aggregate(models.Sum('inv_qty'))['inv_qty__sum']
                obj.qty_inventory_avail = qty_avail_inventory if qty_avail_inventory else 0

                if db_update_initial:
                    obj.save_without_historical_record()
                else:
                    obj.changeReason = 'Update Quantity'
                    obj.save()

                db_update_list.remove(product_name)
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
                    db_update_list.append(new_obj.inv_product.product_name) if new_obj.inv_product.product_name not in db_update_list else db_update_list
                try:
                    if old_obj.inv_product:
                        db_update_list.append(old_obj.inv_product.product_name) if old_obj.inv_product.product_name not in db_update_list else db_update_list
                except Product.DoesNotExist:
                    pass
            elif change.field == 'inv_qty':
                if new_obj.inv_product:
                    db_update_list.append(new_obj.inv_product.product_name) if new_obj.inv_product.product_name not in db_update_list else db_update_list
            elif change.field == 'created_on':
                if new_obj.inv_product:
                    db_update_list.append(new_obj.inv_product.product_name) if new_obj.inv_product.product_name not in db_update_list else db_update_list
        scheduler.add_job(update_product_db, 'date', run_date=timezone.now() + timezone.timedelta(seconds=1), id='update_product_db', replace_existing=True)


@receiver(post_create_historical_record, sender=HistoricalAgvProductionPlan, dispatch_uid="post_update_agv_plan")
def post_update_agv_plan(sender, instance, **kwargs):
    global db_update_list
    new_record = instance.history.first()
    new_obj = new_record.instance
    db_update_list.append(new_obj.product_name.product_name) if new_obj.product_name.product_name not in db_update_list else db_update_list
    scheduler.add_job(update_product_db, 'date', run_date=timezone.now() + timezone.timedelta(seconds=1), id='update_product_db', replace_existing=True)


@receiver(post_create_historical_record, sender=HistoricalAgvQueue, dispatch_uid="post_update_agv_queue")
def post_update_agv_queue(sender, instance, **kwargs):
    global db_update_list
    new_record = instance.history.first()
    new_obj = new_record.instance
    db_update_list.append(new_obj.product_name.product_name) if new_obj.product_name.product_name not in db_update_list else db_update_list
    scheduler.add_job(update_product_db, 'date', run_date=timezone.now() + timezone.timedelta(seconds=1), id='update_product_db', replace_existing=True)


def agv_dummy():
    qs_transfer = AgvTransfer.objects.filter(id=1)
    obj_transfer = get_object_or_404(qs_transfer)
    obj_transfer.x_nav -= 1
    if obj_transfer.x_nav <= -61:
        obj_transfer.x_nav = 31
    obj_transfer.changeReason = 'Simulate AGV Moving'
    obj_transfer.save()


scheduler = BackgroundScheduler()
scheduler.add_job(initial_data, 'date', run_date=timezone.now() + timezone.timedelta(seconds=1), id='initial_data', replace_existing=True)
scheduler.add_job(transfer_check, 'interval', seconds=2, id='transfer_check', replace_existing=True)
scheduler.add_job(robot_check, 'interval', seconds=2, id='robot_check', replace_existing=True)
# scheduler.add_job(agv_dummy, 'interval', seconds=1, id='agv_dummy', replace_existing=True)

print(datetime_now() + 'Program Started')
try:
    db_update_list = list(Product.objects.all().values_list('product_name', flat=True))
except ProgrammingError:
    pass
update_product_db()
