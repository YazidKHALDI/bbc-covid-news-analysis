var Highcharts = require('highcharts');
require('highcharts/modules/wordcloud')(Highcharts);
require('highcharts/modules/map')(Highcharts);
require('highcharts/modules/sankey')(Highcharts);
require('highcharts/modules/dependency-wheel')(Highcharts);
import world from './world.json';
import topology from './world.topo.json';
const $button = document.querySelector("#submit");
const $errorMsg = document.querySelector("#error-msg");
const $startDateInput = document.querySelector("#start_date");
const $endDateInput = document.querySelector("#end_date");

const $numberOfArticsl = document.querySelector("#number_of_articls");
const $strat_date_span = document.querySelector("#span_start_date");
const $end_date_span = document.querySelector("#span_end_date");



const basUrl = 'http://127.0.0.1:8000/';

window.addEventListener('DOMContentLoaded', (event) => {
    fetchArticlsData(basUrl);
});

$startDateInput.addEventListener("change", (event) => {
    if (event.target.value) {
        let date = new Date(event.target.value);
        date.setDate(date.getDate() + 1);
        $endDateInput.setAttribute("min", date.toISOString().split('T')[0]);
    }
});



$button.addEventListener("click", (event) => {

    $errorMsg.innerHTML = '';
    if (($startDateInput.value == '' && $endDateInput.value != '') || ($startDateInput.value != '' && $endDateInput.value == '') || ($startDateInput.value == $endDateInput.value && $startDateInput.value != '')) {
        $errorMsg.innerHTML = 'you should select both dates to get articles of the range date or search with empty dates to get all data';
        return;
    }

    if ($startDateInput.value == '' && $endDateInput.value == '') {
        fetchArticlsData(basUrl);
    } else {
        let starDate = new Date($startDateInput.value);
        let endDate = new Date($endDateInput.value);
        if (starDate > endDate) {
            $errorMsg.innerHTML = 'End date should be greater than Start date';
            return;
        }
        fetchArticlsData(basUrl + `?start_date=${starDate.toISOString().split('T')[0]}&end_date=${endDate.toISOString().split('T')[0]}`);

    }
});



function displayCharts(data) {
    $numberOfArticsl.innerHTML = data.articles.length;
    $strat_date_span.innerHTML = data.start_date_data;
    $end_date_span.innerHTML = data.end_date_data;
    bar_chart(
        'frequency_of_authors',
        `Number of articles per author between ${data.start_date_data} and ${data.end_date_data}`,
        Object.entries(data['frequency_of_authors']).map(([key, value]) => (value.author)),
        'authors',
        Object.entries(data['frequency_of_authors']).map(([key, value]) => (value.count)),
        'Articls',
        '',
        'Articls',
        '#7CB5EC'
    );
    bar_chart(
        'frequency_of_topics',
        `Number of articles per topic between ${data.start_date_data} and ${data.end_date_data}`,
        Object.entries(data['frequency_of_topics']).map(([key, value]) => (value.topic)),
        'contenet',
        Object.entries(data['frequency_of_topics']).map(([key, value]) => (value.count)),
        'topics',
        '',
        'topics',
        '#434348'
    );
    bar_chart(
        'frequency_of_counries',
        `Number of articles per country between ${data.start_date_data} and ${data.end_date_data}`,
        Object.entries(data['frequency_of_countries']).map(([key, value]) => (value.country)),
        'counries',
        Object.entries(data['frequency_of_countries']).map(([key, value]) => (value.count)),
        '',
        '',
        ' Counries',
        '#01359a'
    );


    bubbleChart('author_subjectivity_polarity_bubble',
        Object.entries(data['author_by_topics_subjectivity_polarity']).map(([key, value]) => ({
            author: key,
            x: value.polarity,
            y: value.subjectivity,
            z: value.counter
        }))
    )

    word_cloud(
        'word_cloud_of_topics',
        Object.entries(data['frequency_of_topics']) /* .filter(function(val) { return  val[1].topic  != 'Coronavirus pandemic' } ) */ .map(([key, value]) => ({
            name: value.topic,
            weight: value.count
        })),
        'Topic used',
        'Wordcloud of the use of topics in articles'
    )



    counriesMap('map_of_counries',
        Object.entries(data['frequency_of_countries']).map(([key, value]) => ({
            code3: world.filter(function (cou) {
                return cou.Title.toLowerCase() == value.country.toLowerCase()
            }).length > 0 ? world.filter(function (cou) {
                return cou.Title.toLowerCase() == value.country.toLowerCase()
            })[0].ISO3.toUpperCase() : null,
            name: value.country,
            value: value.count,
            code: world.filter(function (cou) {
                return cou.Title.toLowerCase() == value.country.toLowerCase()
            }).length > 0 ? world.filter(function (cou) {
                return cou.Title.toLowerCase() == value.country.toLowerCase()
            })[0].ISO2.toUpperCase() : null,
        })),
        data['frequency_of_countries'].length > 0 ? data['frequency_of_countries'][0].count + 5 : null,
        'Number of articles per country',
        'Appearance of countries per article',
        'appearance of country in articles'
    );

    article_by_date('article_by_date',
        Object.entries(data['count_articls_per_day']).map(([key, value]) => ([parseInt(value.date) * 1000, value.count])),
        'Publication frequency of news articles',
        'N° articls',
        'Number of articls per day'
    );
    dependency_wheel('dependency_wheel', data['unique_list_of_topics_relations']);

}



function fetchArticlsData(Url) {

    $errorMsg.innerHTML = '';
    fetch(Url)
        .then((response) => {
            if (response.ok) {
                return response.json();
            }
            throw Error(response.statusText);
        })
        .then(async (data) => {
            displayCharts(data);
        }).catch(function (error) {
            $errorMsg.innerHTML = error;
        });
}




function bar_chart(id, Title, x_data, x_title, series_data, series_name, y_title, valueSuffix, barColor) {
    Highcharts.chart(id, {
        chart: {
            type: 'bar',
            height: '100%'
        },
        title: {
            text: Title,
            align: 'left'
        },
        xAxis: {
            categories: x_data,
            title: {
                text: x_title
            }
        },
        yAxis: {
            min: 0,
            title: {
                text: y_title,
                align: 'high'
            },
            labels: {
                overflow: 'justify'
            }
        },
        tooltip: {
            valueSuffix: valueSuffix
        },
        plotOptions: {
            bar: {
                dataLabels: {
                    enabled: true
                }
            }
        },
        legend: {
            enabled: false,
            layout: 'vertical',
            align: 'right',
            verticalAlign: 'top',
            x: -40,
            y: 80,
            floating: true,
            borderWidth: 1,
            backgroundColor: Highcharts.defaultOptions.legend.backgroundColor || '#FFFFFF',
            shadow: true
        },
        credits: {
            enabled: false
        },
        series: [{
            name: series_name,
            data: series_data,
            color: barColor
        }]
    });

}

function ScatterChart(id, data) {
    Highcharts.chart(id, {

        chart: {
            zoomType: 'xy',
            height: '100%'
        },

        boost: {
            useGPUTranslations: true,
            usePreAllocated: true
        },

        accessibility: {
            screenReaderSection: {
                beforeChartFormat: '<{headingTagName}>{chartTitle}</{headingTagName}><div>{chartLongdesc}</div><div>{xAxisDescription}</div><div>{yAxisDescription}</div>'
            }
        },

        xAxis: {
            min: -1,
            max: 1,
            gridLineWidth: 1,
            title: {
                text: 'Polarity'
            }
        },

        yAxis: {
            // Renders faster when we don't have to compute min and max
            min: 0,
            max: 1,
            minPadding: 0,
            maxPadding: 0,
            title: {
                text: 'Subjectivity'
            }
        },

        title: {
            text: 'Sentiment Analysis by authors'
        },

        legend: {
            enabled: false
        },

        series: [{
            type: 'scatter',
            color: '#1140a0',
            data: data,
            marker: {
                radius: 2
            },
            tooltip: {
                followPointer: false,
                pointFormat: '{point.author} [Polarity {point.x:.1f},Subjectivity {point.y:.1f}]'
            }
        }]

    });
}


function word_cloud(id, data, series_name, title) {
    Highcharts.chart(id, {
        accessibility: {
            screenReaderSection: {
                beforeChartFormat: '<h5>{chartTitle}</h5>' +
                    '<div>{chartSubtitle}</div>' +
                    '<div>{chartLongdesc}</div>' +
                    '<div>{viewTableButton}</div>'
            }
        },
        series: [{
            type: 'wordcloud',
            data,
            name: series_name
        }],
        title: {
            text: title,
            align: 'left'
        },
        tooltip: {
            headerFormat: '<span style="font-size: 16px"><b>{point.key} times</b></span><br>'
        }
    });
}



function counriesMap(id, data, max, title, legend_title, series_name) {
    // Prevent logarithmic errors in color calulcation
    data.forEach(function (p) {
        p.value = (p.value < 1 ? 1 : p.value);
    });

    // Initialize the chart
    Highcharts.mapChart(id, {

        chart: {
            map: topology
        },

        title: {
            text: title
        },

        legend: {
            title: {
                text: legend_title,
                style: {
                    color: ( // theme
                        Highcharts.defaultOptions &&
                        Highcharts.defaultOptions.legend &&
                        Highcharts.defaultOptions.legend.title &&
                        Highcharts.defaultOptions.legend.title.style &&
                        Highcharts.defaultOptions.legend.title.style.color
                    ) || 'black'
                }
            }
        },

        mapNavigation: {
            enabled: true,
            buttonOptions: {
                verticalAlign: 'bottom'
            }
        },

        tooltip: {
            backgroundColor: 'none',
            borderWidth: 0,
            shadow: false,
            useHTML: true,
            padding: 0,
            pointFormat: '<span class="f32"><span class="flag {point.properties.hc-key}">' +
                '</span></span> {point.name}<br>' +
                '<span style="font-size:30px">{point.value}</span>',
            positioner: function () {
                return {
                    x: 0,
                    y: 250
                };
            }
        },

        colorAxis: {
            min: 1,
            max: max,
            type: 'logarithmic'
        },

        series: [{
            data: data,
            joinBy: ['iso-a3', 'code3'],
            name: series_name,
            states: {
                hover: {
                    color: '#a4edba'
                }
            }
        }]
    });
}


function article_by_date(id, data, title, y_title, series_name) {
    Highcharts.chart(id, {

        chart: {
            zoomType: 'x'
        },

        title: {
            text: title
        },

        subtitle: {
            text: null
        },

        accessibility: {
            screenReaderSection: {
                beforeChartFormat: '<{headingTagName}>{chartTitle}</{headingTagName}><div>{chartSubtitle}</div><div>{chartLongdesc}</div><div>{xAxisDescription}</div><div>{yAxisDescription:.0f}</div>'
            }
        },

        tooltip: {
            valueDecimals: 2
        },

        xAxis: {
            type: 'datetime',
        },

        yAxis: {
            title: {
                text: y_title
            }
        },
        series: [{
            data: data,
            lineWidth: 1.5,
            name: series_name
        }]

    });
}

function bubbleChart(id, data) {
    Highcharts.chart(id, {

        chart: {
            type: 'bubble',
            plotBorderWidth: 1,
            zoomType: 'xy'
        },

        legend: {
            enabled: false
        },

        title: {
            text: 'Polarity and Subjectivity average per author'
        },

        subtitle: {
            text: null
        },

        accessibility: {
            point: {
                valueDescriptionFormat: '{index}. {point.name}, fat: {point.x}g, sugar: {point.y}g, obesity: {point.z}%.'
            }
        },

        xAxis: {
            gridLineWidth: 1,
            /* min: -1,
            max: 1, */
            title: {
                text: 'Polarity'
            },
            labels: {
                format: '{value}'
            },
            plotLines: [{
                color: 'black',
                dashStyle: 'dot',
                width: 2,
                value: 65,
                label: {
                    rotation: 0,
                    y: 15,
                    style: {
                        fontStyle: 'italic'
                    },
                    text: 'Safe fat intake 65g/day'
                },
                zIndex: 3
            }],
            accessibility: {
                rangeDescription: 'Range: 60 to 100 grams.'
            }
        },

        yAxis: {
            startOnTick: false,
            endOnTick: false,
            /* min: 0,
            max: 1, */
            title: {
                text: 'Subjectivity'
            },
            labels: {
                format: '{value}'
            },
            maxPadding: 0.2,
            plotLines: [{
                color: 'black',
                dashStyle: 'dot',
                width: 2,
                value: 50,
                label: {
                    align: 'right',
                    style: {
                        fontStyle: 'italic'
                    },
                    text: 'Safe sugar intake 50g/day',
                    x: -10
                },
                zIndex: 3
            }],
            accessibility: {
                rangeDescription: 'Range: 0 to 160 grams.'
            }
        },

        tooltip: {
            useHTML: true,
            headerFormat: '<table>',
            pointFormat: '<tr><th colspan="2"><h3>{point.author}</h3></th></tr>' +
                '<tr><th>Polarity:</th><td>{point.x:.2f}</td></tr>' +
                '<tr><th>Subjectivity:</th><td>{point.y:.2f}</td></tr>' +
                '<tr><th>{point.z} articls</th><td></td></tr>',
            footerFormat: '</table>',
            followPointer: true
        },

        plotOptions: {
            series: {
                dataLabels: {
                    enabled: true,
                    format: '{point.author}'
                }
            }
        },

        series: [{
            data: data
                /* [
                               { x: 95, y: 95, z: 13.8, name: 'BE', country: 'Belgium' },
                               { x: 86.5, y: 102.9, z: 14.7, name: 'DE', country: 'Germany' },
                               { x: 80.8, y: 91.5, z: 15.8, name: 'FI', country: 'Finland' },
                               { x: 80.4, y: 102.5, z: 12, name: 'NL', country: 'Netherlands' },
                               { x: 80.3, y: 86.1, z: 11.8, name: 'SE', country: 'Sweden' },
                               { x: 78.4, y: 70.1, z: 16.6, name: 'ES', country: 'Spain' },
                               { x: 74.2, y: 68.5, z: 14.5, name: 'FR', country: 'France' },
                               { x: 73.5, y: 83.1, z: 10, name: 'NO', country: 'Norway' },
                               { x: 71, y: 93.2, z: 24.7, name: 'UK', country: 'United Kingdom' },
                               { x: 69.2, y: 57.6, z: 10.4, name: 'IT', country: 'Italy' },
                               { x: 68.6, y: 20, z: 16, name: 'RU', country: 'Russia' },
                               { x: 65.5, y: 126.4, z: 35.3, name: 'US', country: 'United States' },
                               { x: 65.4, y: 50.8, z: 28.5, name: 'HU', country: 'Hungary' },
                               { x: 63.4, y: 51.8, z: 15.4, name: 'PT', country: 'Portugal' },
                               { x: 64, y: 82.9, z: 31.3, name: 'NZ', country: 'New Zealand' }
                           ] */
                ,
            colorByPoint: true
        }]

    });
}


function dependency_wheel(id, date) {
    let max = 1000;
    if (date.length < max) {
        document.getElementById(id).innerHTML = '';
        document.getElementById(id).style.height = '700px';
        Highcharts.chart(id, {

            title: {
                text: 'Realtaions between topics'
            },

            accessibility: {
                point: {
                    valueDescriptionFormat: '{index}. From {point.from} to {point.to}: {point.weight}.'
                }
            },

            series: [{
                keys: ['from', 'to', 'weight'],
                data: date,
                type: 'dependencywheel',
                name: '',
                dataLabels: {
                    color: '#333',
                    style: {
                        textOutline: 'none'
                    },
                    textPath: {
                        enabled: true
                    },
                    distance: 10
                },
                size: '100%'
            }]

        });
    } else {
        document.getElementById(id).innerHTML = '<h2>Dependency wheel work better with data less than ' + max + '</h2>';
        document.getElementById(id).style.height = '100%';
        document.getElementById(id).style.color = 'red';
        document.getElementById(id).style.fontWeight = 'Bolder';
    }
}