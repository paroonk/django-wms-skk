$(document).ready(function () {
    /************************************************************************************************************************************************/
    /* Date Range Picker */
    var date_format = 'D/M/YY HH:mm'

    $('input[name="date_filter"]').daterangepicker({
        maxDate: moment(),
        timePicker: true,
        timePicker24Hour: true,
        locale: {
            format: date_format,
            applyLabel: str_submit,
            cancelLabel: str_cancel,
            customRangeLabel: str_custom_range,
        },
        ranges: custom_range,
    })
    /************************************************************************************************************************************************/
    $.ajax({
        url: api_historygraph,
        type: 'GET',
        data: {
            'label': $('#id_label').val(),
            'date_filter': $('#id_date_filter').val(),
            'data': $('#id_data').val()
        },
        success: function (response) {
            series = []
            $.each(response.label_list, function (key, value) {
                series.push({ name: value, type: 'line', symbol: 'none', lineStyle: { width: 4 }, data: response.qty[value] })
            })
            Option = {
                tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, textStyle: { fontSize: 12 } },
                legend: { data: response.label_list },
                xAxis: { type: 'category', boundaryGap: false, data: response.dt },
                yAxis: { type: 'value' },
                series: series,
                dataZoom: [{ type: 'slider', start: 0, end: 100 }, { type: 'inside' }],
                toolbox: {
                    show: true,
                    showTitle: false,
                    feature: { saveAsImage: { show: true, title: label_saveAsImage, name: label_toolboxName } },
                    tooltip: { show: true, textStyle: { fontSize: 12 } }
                }
            }
            historyChart.setOption(Option)
        }
    })
    /* Responsive Chart */
    $(window).resize(function () {
        historyChart.resize()
    })
    /************************************************************************************************************************************************/
})
