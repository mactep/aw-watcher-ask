#!/usr/bin/env python3
# SPDX-FileCopyrightText: Bernardo Chrispim Baron <bc.bernardo@hotmail.com>
#
# SPDX-License-Identifier: MIT

"""Export ActivityWatch aw-watcher-ask data to a static HTML visualization."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import typer
import requests


app = typer.Typer()


def list_buckets(base_url: str) -> Dict[str, Any]:
    response = requests.get(f"{base_url}/api/0/buckets")
    response.raise_for_status()
    return response.json()


def find_aw_watcher_ask_bucket(buckets: Dict[str, Any],
                               hostname: Optional[str] = None) -> Optional[str]:
    bucket_pattern = "aw-watcher-ask_"
    
    matching_buckets = [
        bucket_id for bucket_id in buckets.keys()
        if bucket_id.startswith(bucket_pattern)
    ]
    
    if not matching_buckets:
        return None
    
    if hostname:
        target_bucket = f"{bucket_pattern}{hostname}"
        if target_bucket in matching_buckets:
            return target_bucket
        return None
    
    return matching_buckets[0]


def get_all_events(base_url: str, bucket_id: str) -> List[Dict[str, Any]]:
    url = f"{base_url}/api/0/buckets/{bucket_id}/events"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def filter_scale_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    scale_events = []
    for event in events:
        data = event.get('data', {})
        if not data.get('success'):
            continue
        value = data.get('value')
        if value is None or value == '':
            continue
        try:
            float(value)
        except (ValueError, TypeError):
            continue
        if 'min-value' not in data or 'max-value' not in data:
            continue
        scale_events.append(event)
    return scale_events


def get_date_range(events: List[Dict[str, Any]]) -> Tuple[str, str]:
    if not events:
        now = datetime.now(timezone.utc)
        return (now - timedelta(days=7)).isoformat(), now.isoformat()
    
    timestamps = [e['timestamp'] for e in events]
    earliest = min(timestamps)
    latest = max(timestamps)
    return earliest, latest


def generate_html(events: List[Dict[str, Any]], bucket_id: str) -> str:
    scale_events = filter_scale_events(events)
    
    if not scale_events:
        min_scale = 1
        max_scale = 10
    else:
        min_scale = min(float(e['data']['min-value']) for e in scale_events)
        max_scale = max(float(e['data']['max-value']) for e in scale_events)
    
    titles = sorted(set(e.get('data', {}).get('title', 'Unknown') for e in scale_events))
    
    earliest, latest = get_date_range(scale_events)
    
    colors = [
        'rgb(41, 255, 1)',
        'rgb(255, 99, 132)',
        'rgb(54, 162, 235)',
        'rgb(255, 206, 86)',
        'rgb(75, 192, 192)',
        'rgb(153, 102, 255)',
        'rgb(255, 159, 64)',
        'rgb(199, 199, 199)'
    ]
    
    translations = {
        'Anxiety level': 'Nível de ansiedade',
        'Happiness level': 'Nível de felicidade'
    }
    
    embedded_data = json.dumps({
        'events': scale_events,
        'minScale': min_scale,
        'maxScale': max_scale,
        'titles': titles,
        'colors': colors,
        'earliest': earliest,
        'latest': latest,
        'translations': translations
    })
    
    html_template = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Visualização aw-watcher-ask</title>
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            height: calc(100vh - 40px);
        }}
        .header {{
            margin-bottom: 20px;
        }}
        h1 {{
            margin: 0 0 10px 0;
        }}
        .status {{
            color: #666;
            margin-bottom: 20px;
        }}
        .controls {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .date-inputs {{
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
            margin-bottom: 15px;
        }}
        .date-inputs label {{
            font-weight: 500;
        }}
        .date-inputs input {{
            padding: 8px 12px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 14px;
        }}
        .date-inputs input:focus {{
            outline: none;
            border-color: #4a90d9;
        }}
        button {{
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: background-color 0.2s;
        }}
        .btn-primary {{
            background-color: #4a90d9;
            color: white;
        }}
        .btn-primary:hover {{
            background-color: #357abd;
        }}
        .btn-preset {{
            background-color: #fff;
            color: #333;
            border: 1px solid #ccc;
        }}
        .btn-preset:hover {{
            background-color: #e9e9e9;
        }}
        .presets {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .error {{
            color: #d32f2f;
            padding: 10px;
            background: #ffebee;
            border-radius: 4px;
            margin-bottom: 10px;
            display: none;
        }}
        #chart-container {{
            height: calc(100% - 200px);
            min-height: 400px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Visualização aw-watcher-ask</h1>
        <p class="status">Carregando...</p>
    </div>
    
    <div class="controls">
        <div id="error" class="error"></div>
        
        <div class="date-inputs">
            <label for="start-date">Início:</label>
            <input type="datetime-local" id="start-date">
            <label for="end-date">Fim:</label>
            <input type="datetime-local" id="end-date">
            <button class="btn-primary" id="apply-btn">Aplicar</button>
        </div>
        
        <div class="presets">
            <button class="btn-preset" id="btn-7days">Últimos 7 dias</button>
            <button class="btn-preset" id="btn-30days">Últimos 30 dias</button>
            <button class="btn-preset" id="btn-all">Todo o período</button>
        </div>
    </div>
    
    <div id="chart-container">
        <canvas id="chart"></canvas>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/moment@2.27.0"></script>
    <script src="https://cdn.jsdelivr.net/npm/moment@2.27.0/locale/pt-br.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-moment@0.1.1"></script>

    <script>
        moment.locale('pt-BR');
        const data = {embedded_data};
        let chart = null;
        
        function translateTitle(title) {{
            return data.translations[title] || title;
        }}
        
        function showError(message) {{
            const errorDiv = document.getElementById('error');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            setTimeout(() => {{
                errorDiv.style.display = 'none';
            }}, 5000);
        }}
        
        function toLocalDateTime(isoString) {{
            const date = new Date(isoString);
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            return `${{year}}-${{month}}-${{day}}T${{hours}}:${{minutes}}`;
        }}
        
        function toISOString(dateTimeLocal) {{
            const date = new Date(dateTimeLocal);
            return date.toISOString();
        }}
        
        function formatBrazilianDate(isoString) {{
            const date = new Date(isoString);
            const day = String(date.getDate()).padStart(2, '0');
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const year = date.getFullYear();
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            return `${{day}}/${{month}}/${{year}} ${{hours}}:${{minutes}}`;
        }}
        
        function formatBrazilianNumber(value) {{
            return value.toFixed(1).replace('.', ',');
        }}
        
        function filterEvents(events, start, end) {{
            const startDate = new Date(start);
            const endDate = new Date(end);
            return events.filter(e => {{
                const ts = new Date(e.timestamp);
                return ts >= startDate && ts <= endDate;
            }});
        }}
        
        function aggregateByHour(events, startDate, endDate) {{
            const hourMap = new Map();
            
            events.forEach(event => {{
                const date = new Date(event.timestamp);
                const hourTimestamp = new Date(
                    date.getFullYear(),
                    date.getMonth(),
                    date.getDate(),
                    date.getHours()
                ).getTime();
                
                if (!hourMap.has(hourTimestamp)) {{
                    hourMap.set(hourTimestamp, {{ sum: 0, count: 0, reasons: new Set() }});
                }}
                
                const bucket = hourMap.get(hourTimestamp);
                bucket.sum += parseFloat(event.data.value);
                bucket.count += 1;
                
                const reason = event.data.reason?.trim();
                if (reason) {{
                    reason.split(',').map(r => r.trim()).filter(r => r).forEach(r => bucket.reasons.add(r));
                }}
            }});
            
            const result = [];
            let current = new Date(startDate);
            current.setMinutes(0, 0, 0);
            
            while (current <= endDate) {{
                const hourTimestamp = current.getTime();
                if (hourMap.has(hourTimestamp)) {{
                    const bucket = hourMap.get(hourTimestamp);
                    result.push({{
                        x: current.toISOString(),
                        y: bucket.sum / bucket.count,
                        reason: bucket.reasons.size > 0 
                            ? Array.from(bucket.reasons).map(r => `• ${{r}}`).join('<br>') 
                            : ''
                    }});
                }}
                current.setHours(current.getHours() + 1);
            }}
            
            return result;
        }}
        
        function aggregateByDay(events, startDate, endDate) {{
            const dayMap = new Map();
            
            events.forEach(event => {{
                const date = new Date(event.timestamp);
                const dayTimestamp = new Date(
                    date.getFullYear(),
                    date.getMonth(),
                    date.getDate()
                ).getTime();
                
                if (!dayMap.has(dayTimestamp)) {{
                    dayMap.set(dayTimestamp, {{ sum: 0, count: 0, reasons: new Set() }});
                }}
                
                const bucket = dayMap.get(dayTimestamp);
                bucket.sum += parseFloat(event.data.value);
                bucket.count += 1;
                
                const reason = event.data.reason?.trim();
                if (reason) {{
                    reason.split(',').map(r => r.trim()).filter(r => r).forEach(r => bucket.reasons.add(r));
                }}
            }});
            
            const result = [];
            let current = new Date(startDate);
            current.setHours(0, 0, 0, 0);
            
            while (current <= endDate) {{
                const dayTimestamp = current.getTime();
                if (dayMap.has(dayTimestamp)) {{
                    const bucket = dayMap.get(dayTimestamp);
                    result.push({{
                        x: current.toISOString(),
                        y: bucket.sum / bucket.count,
                        reason: bucket.reasons.size > 0 
                            ? Array.from(bucket.reasons).map(r => `• ${{r}}`).join('<br>') 
                            : ''
                    }});
                }}
                current.setDate(current.getDate() + 1);
            }}
            
            return result;
        }}
        
        function getAggregationConfig(start, end) {{
            const duration = new Date(end) - new Date(start);
            if (duration > 24 * 60 * 60 * 1000) {{
                return {{
                    aggregFn: aggregateByDay,
                    timeUnit: 'day',
                    displayFormat: 'DD/MM/YYYY'
                }};
            }}
            return {{
                aggregFn: aggregateByHour,
                timeUnit: 'hour',
                displayFormat: 'HH:mm'
            }};
        }}
        
        function renderChart(filteredEvents, start, end) {{
            if (filteredEvents.length === 0) {{
                document.getElementById('chart-container').innerHTML = '<p>Nenhuma resposta do tipo escala encontrada para o período selecionado.</p>';
                document.querySelector('.status').textContent = `Nenhum evento encontrado de ${{formatBrazilianDate(start)}} a ${{formatBrazilianDate(end)}}`;
                return;
            }}
            
            const startDate = new Date(start);
            const endDate = new Date(end);
            
            const groupedEvents = new Map();
            data.titles.forEach(title => {{
                groupedEvents.set(title, filteredEvents.filter(e => e.data.title === title));
            }});
            
            const aggregConfig = getAggregationConfig(start, end);
            
            const datasets = data.titles.map((title, index) => {{
                const titleEvents = groupedEvents.get(title) || [];
                const aggregatedData = aggregConfig.aggregFn(titleEvents, startDate, endDate);
                
                return {{
                    label: translateTitle(title),
                    data: aggregatedData,
                    borderColor: data.colors[index % data.colors.length],
                    backgroundColor: data.colors[index % data.colors.length].replace('rgb', 'rgba').replace(')', ', 0.1)'),
                    fill: true,
                    tension: 0.25
                }};
            }});
            
            document.querySelector('.status').textContent = `Exibindo ${{filteredEvents.length}} eventos de ${{formatBrazilianDate(start)}} a ${{formatBrazilianDate(end)}}`;
            
            const chartContainer = document.getElementById('chart-container');
            chartContainer.innerHTML = '<canvas id="chart"></canvas>';
            const ctx = document.getElementById('chart').getContext('2d');
            
            if (chart) {{
                chart.destroy();
            }}
            
            chart = new Chart(ctx, {{
                type: 'line',
                data: {{
                    datasets: datasets
                }},
                options: {{
                    scales: {{
                        x: {{
                            type: 'time',
                            time: {{
                                unit: aggregConfig.timeUnit,
                                displayFormats: {{
                                    [aggregConfig.timeUnit]: aggregConfig.displayFormat
                                }}
                            }},
                            ticks: {{
                                format: aggregConfig.displayFormat
                            }}
                        }},
                        y: {{
                            min: Math.floor(data.minScale - (data.maxScale - data.minScale) * 0.1),
                            max: Math.ceil(data.maxScale + (data.maxScale - data.minScale) * 0.1),
                            title: {{
                                display: true,
                                text: 'Valor da Escala'
                            }},
                            ticks: {{
                                stepSize: (function() {{
                                    const range = Math.ceil(data.maxScale + (data.maxScale - data.minScale) * 0.1) - Math.floor(data.minScale - (data.maxScale - data.minScale) * 0.1);
                                    if (range <= 0) {{
                                        return 1;
                                    }}
                                    return Math.pow(10, Math.floor(Math.log10(range)) - 1);
                                }}())
                            }}
                        }}
                    }},
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        tooltip: {{
                            mode: 'nearest',
                            intersect: false,
                            callbacks: {{
                                label: function(context) {{
                                    let label = context.dataset.label || '';
                                    if (label) {{
                                        label += ': ';
                                    }}
                                    label += formatBrazilianNumber(context.parsed.y);
                                    return label;
                                }},
                                afterLabel: function(context) {{
                                    const point = context.raw;
                                    if (point.reason && point.reason.trim()) {{
                                        return point.reason.split('<br>');
                                    }}
                                    return '';
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }}
        
        function updateChart() {{
            const startValue = document.getElementById('start-date').value;
            const endValue = document.getElementById('end-date').value;
            
            if (!startValue || !endValue) {{
                showError('Por favor, selecione as datas de início e fim');
                return;
            }}
            
            const startIso = toISOString(startValue);
            const endIso = toISOString(endValue);
            
            if (new Date(startIso) > new Date(endIso)) {{
                showError('A data de início deve ser anterior à data de fim');
                return;
            }}
            
            const filtered = filterEvents(data.events, startIso, endIso);
            renderChart(filtered, startIso, endIso);
        }}
        
        function setAllTime() {{
            const startDateInput = document.getElementById('start-date');
            const endDateInput = document.getElementById('end-date');
            
            startDateInput.value = toLocalDateTime(data.earliest);
            endDateInput.value = toLocalDateTime(data.latest);
            
            updateChart();
        }}
        
        function setPreset(days) {{
            const now = new Date();
            const startDate = new Date(now);
            startDate.setDate(startDate.getDate() - days);
            
            const startDateInput = document.getElementById('start-date');
            const endDateInput = document.getElementById('end-date');
            
            startDateInput.value = toLocalDateTime(startDate.toISOString());
            endDateInput.value = toLocalDateTime(now.toISOString());
            
            updateChart();
        }}
        
        document.addEventListener('DOMContentLoaded', function() {{
            document.getElementById('apply-btn').addEventListener('click', updateChart);
            document.getElementById('start-date').addEventListener('keypress', function(e) {{
                if (e.key === 'Enter') updateChart();
            }});
            document.getElementById('end-date').addEventListener('keypress', function(e) {{
                if (e.key === 'Enter') updateChart();
            }});
            document.getElementById('btn-7days').addEventListener('click', () => setPreset(7));
            document.getElementById('btn-30days').addEventListener('click', () => setPreset(30));
            document.getElementById('btn-all').addEventListener('click', setAllTime);
            
            setAllTime();
        }});
    </script>
</body>
</html>
"""
    
    return html_template


@app.command()
def export(
    hostname: Optional[str] = typer.Option(None, '--hostname', help='Bucket hostname (default: auto-detect)'),
    output: str = typer.Option('export_visualization.html', '--output', '-o', help='Output HTML file'),
    base_url: str = typer.Option('http://localhost:5600', '--base-url', help='ActivityWatch API base URL'),
):
    """Export aw-watcher-ask data to a static HTML visualization."""
    
    try:
        buckets = list_buckets(base_url)
    except requests.RequestException as e:
        typer.echo(f"Error: Failed to connect to ActivityWatch at {base_url}: {e}", err=True)
        raise typer.Exit(1)
    
    bucket_id = find_aw_watcher_ask_bucket(buckets, hostname)
    
    if not bucket_id:
        if hostname:
            typer.echo(f"Error: No aw-watcher-ask bucket found for hostname '{hostname}'", err=True)
        else:
            typer.echo("Error: No aw-watcher-ask buckets found. Please check ActivityWatch server.", err=True)
        raise typer.Exit(1)
    
    if not hostname:
        matching_buckets = [b for b in buckets.keys() if b.startswith('aw-watcher-ask_')]
        if len(matching_buckets) > 1:
            typer.echo(f"Found multiple buckets, using: {bucket_id}", err=True)
    
    try:
        events = get_all_events(base_url, bucket_id)
    except requests.RequestException as e:
        typer.echo(f"Error: Failed to fetch events: {e}", err=True)
        raise typer.Exit(1)
    
    html_content = generate_html(events, bucket_id)
    
    output_path = Path(output)
    output_path.write_text(html_content)
    
    typer.echo(f"Exported visualization to: {output_path.absolute()}")


if __name__ == '__main__':
    app()
