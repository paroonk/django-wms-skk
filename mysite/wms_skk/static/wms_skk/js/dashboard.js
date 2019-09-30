$(document).ready(function() {
    $(window).resize(function() {
        overviewChart.resize();
        usageChart.resize();
    });

    $('input:radio[name="overview_plant_id"], input:radio[name="overview_value_type"]').change(function() {
        overview_plant_id_value = parseInt($('input:radio[name="overview_plant_id"]:checked').val());
        overview_value_type_value = parseInt($('input:radio[name="overview_value_type"]:checked').val());
        selected_option = overview_plant_id_value + overview_value_type_value;
        overviewChart.setOption(overviewOption[selected_option]);
    });

    $('input:radio[name="overview_plant_id"]:radio:first').trigger('change');
});
