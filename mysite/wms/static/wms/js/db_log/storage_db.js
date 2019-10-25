$(document).ready(function() {
    var table = $('#dataTable').DataTable({
        dom: "<'row'<'col-sm-6'B><'col-sm-6'f>>" + "<'row'<'col-sm-12'tr>>" + "<'row'<'col-sm-5'i><'col-sm-7'p>>",
        buttons: [
            'colvis', 'excel', 'print'
        ],
        order: [[ 1, 'asc' ]],
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, 'All']],
        columns: [
            { data: 'storage_id', className: "text-left" },
            { data: 'is_inventory', className: "text-center" },
            { data: 'storage_for', className: "text-left" },
            { data: 'have_inventory', className: "text-center" },
            { data: 'inv_product', className: "text-left" },
            { data: 'name_eng', className: "text-left" },
            { data: 'inv_qty', className: "text-right" },
            { data: 'lot_name', className: "text-left" },
            { data: 'created_on', className: "text-left" },
            { data: 'updated_on', className: "text-left" },
        ],
        searching: true,
        processing: true,
        serverSide: true,
        stateSave: true,
        ajax: json_data,
        scrollY: 600,
        deferRender: true,
        scroller: true,
    });
});