$(document).ready(function() {
    var table = $('#dataTable').DataTable({
        dom: "<'row'<'col-sm-6'B><'col-sm-6'f>>" + "<'row'<'col-sm-12'tr>>" + "<'row'<'col-sm-5'i><'col-sm-7'p>>",
        buttons: [
            'colvis', 'excel', 'print'
        ],
        order: [[ 2, 'asc' ], [ 4, 'desc' ]],
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, 'All']],
        columns: [
            { data: 'product_name', className: "text-left" },
            { data: 'name_eng', className: "text-left" },
            { data: 'plant', className: "text-center" },
            { data: 'qty_limit', className: "text-right" },
            { data: 'qty_storage', className: "text-right" },
            { data: 'qty_inventory', className: "text-right" },
            { data: 'qty_buffer', className: "text-right" },
            { data: 'qty_misplace', className: "text-right" },
            { data: 'qty_total', className: "text-right" },
            { data: 'qty_storage_avail', className: "text-right" },
            { data: 'qty_inventory_avail', className: "text-right" },
        ],
        columnDefs: [
            {
                targets: [0, 2],
                render: function(data, type, row, meta) {
                    if (type === 'display') { data = '<a href=' + url_storage_db.replace('pk', encodeURIComponent(data)) + '>' + data + '</a>'; }
                    return data;
                }
            }
        ],
        searching: true,
        processing: true,
        serverSide: true,
        stateSave: true,
        ajax: json_data,
        scrollY: 600,
        deferRender: true,
        scroller: true,
        orderCellsTop: true,
    });

    table.search($('input[name=q]').val()).draw();

    $('input[name=q]').keyup(function() {
          table.search($(this).val()).draw();
    });

    table.on('search.dt', function() {
        var value = $('.dataTables_filter input').val();
        $('input[name=q]').val(value);
    });

});