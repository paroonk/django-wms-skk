$(document).ready(function () {
    /************************************************************************************************************************************************/
    $('input:radio[name="overview_plant_id"], input:radio[name="overview_value_type"]').change(function () {
        $.ajax({
            url: api_overviewgraph,
            type: 'GET',
            data: {
                'plant_id': $('input:radio[name="overview_plant_id"]:checked').val(),
                'value_type': $('input:radio[name="overview_value_type"]:checked').val()
            },
            success: function (response) {
                Option = {
                    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, textStyle: { fontSize: 12 } },
                    legend: { data: lebel_legendList },
                    xAxis: { data: response.product_name, axisLabel: { fontSize: 9, rotate: 25 } },
                    yAxis: { type: 'value', min: null, max: null, axisLabel: { formatter: '{value} Bags' } },
                    color: ['#003366', 'purple', 'red', 'silver'],
                    series: [
                        { name: lebel_legendList[0], type: 'bar', stack: 'component', data: response.qty_inventory },
                        { name: lebel_legendList[1], type: 'bar', stack: 'component', data: response.qty_buffer },
                        { name: lebel_legendList[2], type: 'bar', stack: 'component', data: response.qty_misplace },
                        { name: lebel_legendList[3], type: 'bar', stack: 'component', data: response.qty_avail_storage }
                    ],
                    toolbox: {
                        show: true,
                        showTitle: false,
                        feature: { saveAsImage: { show: true, title: label_saveAsImage, name: 'Stock Overview' }, },
                        tooltip: { show: true, textStyle: { fontSize: 12 } }
                    }
                }
                overviewChart.setOption(Option)
            }
        })
    })

    $('input:radio[name="overview_plant_id"]:radio:first').trigger('change')
    /************************************************************************************************************************************************/
    $.ajax({
        url: api_usagegraph,
        type: 'GET',
        success: function (response) {
            Option = {
                tooltip: { trigger: 'item', formatter: '{b}<br/>{c} ({d}%)', textStyle: { fontSize: 12 } },
                series: [{
                    name: 'Inventory', type: 'pie', radius: ['0%', '80%'], center: ['50%', '50%'],
                    data: response.qty_inventory, itemStyle: { emphasis: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
                }],
                toolbox: { show: true, showTitle: false, feature: { saveAsImage: { show: true, title: label_saveAsImage, name: 'Stock Usage' } }, tooltip: { show: true, textStyle: { fontSize: 12 } } }
            }
            usageChart.setOption(Option)
        }
    })
    /************************************************************************************************************************************************/
    $(window).resize(function () {
        overviewChart.resize()
        usageChart.resize()
    })
    /************************************************************************************************************************************************/
})
