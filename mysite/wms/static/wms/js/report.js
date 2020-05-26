$(document).ready(function () {
    /************************************************************************************************************************************************/
    $.ajax({
        url: api_report,
        type: 'GET',
        success: function (response) {
            var data_list = []
            $.each(response, function(key, value) {
                data_list.push(value[Object.keys(value)[0]])
            })

            var series_list = []
            $.each(label_legendList, function(key, value) {
                series_list.push({
                    type: 'bar',
                    stack: 'component',
                })
            })

            Option = {
                tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, textStyle: { fontSize: 12 } },
                legend: { data: label_legendList },
                dataset: {
                    dimensions: $.merge(index_name, label_legendList),
                    source: response
                },
                xAxis: {type: 'value'},
                yAxis: {type: 'category', data: data_list.reverse()},
                series: series_list,
                toolbox: {
                    show: true,
                    showTitle: false,
                    feature: { saveAsImage: { show: true, title: label_saveAsImage, name: chart_savename }, },
                    tooltip: { show: true, textStyle: { fontSize: 12 } }
                }
            }
            reportChart.setOption(Option)
        }
    })

    /************************************************************************************************************************************************/
    $(window).resize(function () {
        reportChart.resize()
    })
    /************************************************************************************************************************************************/
})
