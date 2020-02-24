def check_path(agv_no, obj_transfer, pattern, agv_x, agv_y, target_col, target_row):
    global send_cmd_hold, x_check, y_check

    # print(datetime_now() + 'Recalculate Route for AGV #{}'.format(agv_no))
    agv_col, agv_row = position_cal(agv_x, agv_y)
    if agv_col == target_col and agv_row == target_row:
        obj_coor = get_object_or_404(Coordinate, layout_col=agv_col, layout_row=agv_row)
        x_check[agv_no] = obj_coor.coor_x
        y_check[agv_no] = obj_coor.coor_y

        path_agv = Point(obj_coor.coor_x, obj_coor.coor_y)
    else:
        runway_top = 8
        runway_mid = 9
        runway_bot = 10
        runway_row = runway_top if agv_no == 1 else runway_bot

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

        # Start point offset
        dist_offset_start = 0.1
        df_route.iloc[0, df_route.columns.get_loc('coor_x')], df_route.iloc[0, df_route.columns.get_loc('coor_y')] = dist_compensate(
            df_route['coor_x'].iloc[1], df_route['coor_y'].iloc[1], df_route['coor_x'].iloc[0], df_route['coor_y'].iloc[0], dist_offset_start
        )

        # Final point offset
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

        # print(' AGV #{}, Pattern = {}'.format(agv_no, pattern))
        # print(' Target x = {:.6f}, y = {:.6f}'.format(x_check[agv_no], y_check[agv_no]))
        # print(df_route.to_string(index=False))

        # Check path intersect before sending command
        intersect = False
        x_list = [df_route['layout_col'].iloc[i] for i in range(len(df_route))]
        y_list = [df_route['layout_row'].iloc[i] for i in range(len(df_route))]
        path_agv = LineString([(x_list[i], y_list[i]) for i in range(len(df_route))])

        # qs_transfer_other = AgvTransfer.objects.exclude(id=agv_no).exclude(run=0)
        # for obj_transfer_other in qs_transfer_other:
        #     agv_x_other, agv_y_other, agv_beta_other = transfer_adjust(obj_transfer_other)
        #     agv_col_other, agv_row_other = position_cal(agv_x_other, agv_y_other)
        #     x_list_other = [obj_transfer_other.col1, obj_transfer_other.col2, obj_transfer_other.col3, obj_transfer_other.col4, obj_transfer_other.col5]
        #     y_list_other = [obj_transfer_other.row1, obj_transfer_other.row2, obj_transfer_other.row3, obj_transfer_other.row4, obj_transfer_other.row5]
        #     if int(obj_transfer_other.qty) > 1:
        #         path_other = LineString([(x_list_other[i], y_list_other[i]) for i in range(int(obj_transfer_other.qty))])
        #     else:
        #         path_other = Point(x_list_other[0], y_list_other[0])
        #     intersect = intersect or path_agv.intersects(path_other)

        # if not intersect:
        #     obj_transfer.pattern = float(pattern)
        #     obj_transfer.qty = float(len(df_route))
        #     obj_transfer.x1 = df_route['coor_x'].iloc[0] if len(df_route) > 0 else 0
        #     obj_transfer.x2 = df_route['coor_x'].iloc[1] if len(df_route) > 1 else 0
        #     obj_transfer.x3 = df_route['coor_x'].iloc[2] if len(df_route) > 2 else 0
        #     obj_transfer.x4 = df_route['coor_x'].iloc[3] if len(df_route) > 3 else 0
        #     obj_transfer.x5 = df_route['coor_x'].iloc[4] if len(df_route) > 4 else 0
        #     obj_transfer.y1 = df_route['coor_y'].iloc[0] if len(df_route) > 0 else 0
        #     obj_transfer.y2 = df_route['coor_y'].iloc[1] if len(df_route) > 1 else 0
        #     obj_transfer.y3 = df_route['coor_y'].iloc[2] if len(df_route) > 2 else 0
        #     obj_transfer.y4 = df_route['coor_y'].iloc[3] if len(df_route) > 3 else 0
        #     obj_transfer.y5 = df_route['coor_y'].iloc[4] if len(df_route) > 4 else 0
        #     obj_transfer.col1 = df_route['layout_col'].iloc[0] if len(df_route) > 0 else 0
        #     obj_transfer.col2 = df_route['layout_col'].iloc[1] if len(df_route) > 1 else 0
        #     obj_transfer.col3 = df_route['layout_col'].iloc[2] if len(df_route) > 2 else 0
        #     obj_transfer.col4 = df_route['layout_col'].iloc[3] if len(df_route) > 3 else 0
        #     obj_transfer.col5 = df_route['layout_col'].iloc[4] if len(df_route) > 4 else 0
        #     obj_transfer.row1 = df_route['layout_row'].iloc[0] if len(df_route) > 0 else 0
        #     obj_transfer.row2 = df_route['layout_row'].iloc[1] if len(df_route) > 1 else 0
        #     obj_transfer.row3 = df_route['layout_row'].iloc[2] if len(df_route) > 2 else 0
        #     obj_transfer.row4 = df_route['layout_row'].iloc[3] if len(df_route) > 3 else 0
        #     obj_transfer.row5 = df_route['layout_row'].iloc[4] if len(df_route) > 4 else 0
        #     obj_transfer.changeReason = 'AGV Update Pattern and Coordinate'
        #     obj_transfer.save()
        else:
            pass

    return path_agv