from dash import Dash, dcc, html, dash_table, Input, Output, callback
import dash_bootstrap_components as dbc
import dash_daq as daq
import dash_ag_grid 
import pandas as pd
import requests


API_URL_SENSORS = "http://localhost:5001/read-sensors"
API_URL_HISTORY = "http://localhost:5001/data"

external_stylesheets = [
    {
        "href": "/assets/style.css",
        "rel": "stylesheet",
    },
]

app = Dash(
    __name__,
    external_stylesheets=[external_stylesheets, dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True  # ✅ add this
)

app.title = "Exawater"


app.layout = html.Div(
    children=[
    
        #left Div
        html.Div(
            children=[
                html.Div(
                    children=[
                        html.P(children="Fan Speed Level"), #needs connection to data variable fan_speed
                        daq.Gauge(
                            min=0,
                            color="#68C5FF",
                            max=5,
                            value=3,
                            scale={'start': 0, 'interval': 1, 'labelInterval': 1},
                            size=120,
                            showCurrentValue=True
                        )
                    ],
                    className="fan-speed box"
                    
                ),
                html.Div(
                    children=[
                        html.P(children=" Water Chiller Temp ℃"), #needs connection to data variable chiller_temp
                        daq.Thermometer(
                            value=10,
                            max=20,
                            min=0,
                            units="℃",
                            height=110,
                            #color="FFFFFF",
                            showCurrentValue=True
                        )  
                    ],
                    className="chiller-temp box"
                    
                ),
                html.Div(
                    children=[
                        html.P("Total Water Collected"), #needs connection to data variable current_weight
                        daq.Tank(
                        id="progress-gauge",
                        color="#86D1FF",
                        height=140,
                        units="Liters",
                        value=3,
                        max=6,
                        min=0,
                        textColor="FFFFFF",
                        showCurrentValue=True,  # default size 200 pixel
                        ),
                    ],
                    className= "water-collection box"
                    
                ),
            ],
            className="header-left"
        ),

        # Center Div
        html.Div(
            children = 
                html.Div(
                    children=[
                        html.H1(children="Current System Metrics"),

                        dcc.Tabs(id='tabs-example-1', value='tab-1', children=[
                            dcc.Tab(label='Latest', value='tab-1'),
                            dcc.Tab(label='History', value='tab-2'),
                        ]),
                        html.Div(id='tabs-example-content-1')
                    ],
                    className="box",
                     style={
                        "backgroundColor": "#1e2130",
                        }

                ),
            className="header-center",
           
        ),

        # Right Div
        

        html.Div(
            children=[
                html.Div(
                    children=[
                        html.H2(children= "Optimal Settings"),
                    ],
                    className= "optimal-box",
                    style= {"font-weight":"bold"}
                ),

                html.Div(
                    children=[
                        html.P(children="Fan Speed Level"), #needs connection to optimizing dataset
                        daq.LEDDisplay(
                            id='optimal-fan-speed',
                            size=25,
                            value=3,
                            color="#027f40",
                            backgroundColor="#86D1FF"
                        )
                    ],
                    className="box center-vertical",
                    style={ "height":"40%"}
                ),

                html.Div(
                    children=[
                        html.P(children="Water Chiller Temperature ℃"), #needs connection to optimizing dataset
                        daq.LEDDisplay(
                            id='optimal-chiller-temp',
                            size=25,
                            value=7,
                            color="#118921",
                            backgroundColor="#86D1FF"
                        )
                        
                    ],
                    className="box center-vertical",
                    style={ "height":"50%"}
                ),
                html.Div(
                    children=[
                        html.P("Optimized Water Flow Rate"), #needs connection to optimizing dataset
                        html.P(" mL/hr"),
                    ],
                    className= "box center-vertical",
                    style={ "height":"35%"}
                ),
                html.Div(
                    children=[
                        html.P("Optimized Power Usage"), #needs connection to optimizing dataset
                        html.P(" kWh"),
                    ],
                    className= "box center-vertical",
                    style={ "height":"35%"}
                ),
                   
            ],
            className="header-right",
        ),
        
    ],
    className="header",
    style={
        "minHeight": "99vh",  # full viewport height
        "display": "flex",
        "flexDirection": "row",
        "align-items": "flex-start",
        "backgroundColor": "#1e2130",
        "margins" : "0px"
    }

)

def fetch_history():
    print("Fetching history from API...")

    try:
        response = requests.get(API_URL_HISTORY, timeout=5)
        response.raise_for_status()

        df = pd.DataFrame(response.json())
        

        if df.empty:
            return df

        df["time"] = pd.to_datetime(df["time"], format="ISO8601")

        # OPTIONAL but recommended for ESP32 alignment
        df["time"] = df["time"].dt.round("2s")

        # TRUE pivot (no aggregation)
        df = df.pivot(
            index="time",
            columns="sensor_type",
            values="value"
        ).reset_index()

        df = df.sort_values("time", ascending=False)
        
        
        return df

    except Exception as e:
        print(f"Unexpected error: {e}")
        return pd.DataFrame()
@callback(
    Output('tabs-example-content-1', 'children'),
    Input('tabs-example-1', 'value')
) 

def render_content(tab):
    
    if tab == 'tab-1':
        df = fetch_history()
    
        latest = df.sort_values("time", ascending=False).head(1)
        power_total = latest.get("apower_1") + latest.get("apower_2")
        power_total = round(power_total,2)

        ambient_temp = [
            dbc.CardHeader("Inside Temp"),
            dbc.CardBody(
                [
                    html.P(
                        f"{latest.get('ambient_temp').item()} ℃",
                        #latest.get("ambient_temp"),
                        #f"{latest.get("ambient_temp").values([1.])} C",
                        className="card-text",
                    ),
                ],
            ),
        ]
        ambient_temp_outside = [
            dbc.CardHeader("Ambient Temp"),
            dbc.CardBody(
                [
                    html.P(
                        f"{latest.get("ambient_temp_outside").item()} ℃",
                        className="card-text",
                    ),
                ]
            ),
        ]
        coil_temp_bot = [
            dbc.CardHeader("Inlet Coil Temp"),
            dbc.CardBody(
                [
                    html.P(
                        f"{latest.get("coil_temp_bot").item()} ℃",
                        className="card-text",
                    ),
                ]
            ),
        ]
        coil_temp_mid = [
            dbc.CardHeader("Mid Coil Temp"),
            dbc.CardBody(
                [
                    html.P(
                        f"{latest.get("coil_temp_mid").item()} ℃",
                        className="card-text",
                    ),
                ]
            ),
        ]
        coil_temp_top = [
            dbc.CardHeader("Outlet Coil Temp"),
            dbc.CardBody(
                [
                    html.P(
                        f"{latest.get("coil_temp_top").item()} ℃",
                        className="card-text",
                    ),
                ]
            ),
        ]
        dew_point_inside = [
            dbc.CardHeader("Inside Dew Point"),
            dbc.CardBody(
                [
                    html.P(
                        f"{latest.get("dew_point_inside").item()} ℃",
                        className="card-text",
                    ),
                ]
            ),
        ]
        dew_point_outside = [
            dbc.CardHeader("Ambient Dew Point"),
            dbc.CardBody(
                [
                    html.P(
                        f"{latest.get("dew_point_outside").item()} ℃",
                        className="card-text",
                    ),
                ]
            ),
        ]
        humidity = [
            dbc.CardHeader("Inside Humidity"),
            dbc.CardBody(
                [
                    html.P(
                        f"{latest.get("humidity").item()} %",
                        className="card-text",
                    ),
                ]
            ),
        ]
        humidity_outside = [
            dbc.CardHeader("Ambient Humidity"),
            dbc.CardBody(
                [
                    html.P(
                        f"{latest.get("humidity_outside").item()} %",
                        className="card-text",
                    ),
                ]
            ),
        ]
        water_rate_ml_hr = [
            dbc.CardHeader("Water Production Rate"),
            dbc.CardBody(
                [
                    html.P(
                        f"{latest.get("water_rate_ml_hr").item()} mL/hr",
                        className="card-text",
                    ),
                ]
            ),
        ]
        total_power = [
            dbc.CardHeader("Total Power Usage"),
            dbc.CardBody(
                [
                    html.P(
                        f"{power_total.item()} kWh",
                        className="card-text",
                    ),
                ]
            ),
        ]
        proj_water_rate = [
            dbc.CardHeader("Projected Water Production Rate"),
            dbc.CardBody(
                [
                    html.P(
                        f"{latest.get("water_rate_ml_hr").item()} mL/hr", #needs to connect to projection data
                        className="card-text",
                    ),
                ]
            ),
        ]
        proj_total_power = [
            dbc.CardHeader("Projected Total Power Usage"),
            dbc.CardBody(
                [
                    html.P(
                        f"{power_total.item()} kWh", #needs to connect to projection data
                        className="card-text",
                    ),
                ]
            ),
        ]

        return html.Div([
                    
            dbc.Row(
                [
                    
                    dbc.Col(dbc.Card(ambient_temp_outside, color="#00628e", inverse=True,style={"font-size": 20})),
                    dbc.Col(dbc.Card(humidity_outside, color="#49abc8", inverse=True,style={"font-size": 20})),
                    dbc.Col(dbc.Card(dew_point_outside, color="#266774", inverse=True,style={"font-size": 20})),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(dbc.Card(ambient_temp, color="#00628e", inverse=True,style={"font-size": 20})),
                    dbc.Col(dbc.Card(humidity, color="#49abc8", inverse=True,style={"font-size": 20})),
                    dbc.Col(dbc.Card(dew_point_inside, color="#266774", inverse=True,style={"font-size": 20})),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(dbc.Card(coil_temp_top, color="#00364D", inverse=True,style={"font-size": 20})),
                    dbc.Col(dbc.Card(coil_temp_mid, color="#00364D", inverse=True,style={"font-size": 20})),
                    dbc.Col(dbc.Card(coil_temp_bot, color="#00364D", inverse=True,style={"font-size": 20})),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(dbc.Card(water_rate_ml_hr, color="#aed0d6",style={"font-size": 20})),
                    dbc.Col(dbc.Card(total_power, color="#aed0d6",style={"font-size": 20})),
                    
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(dbc.Card(proj_water_rate, color="white", style={"font-size": 20},className="border border-info border-4")),
                    dbc.Col(dbc.Card(proj_total_power, color="white", style={"font-size": 20}, className="border border-info border-4")),
                ],
                className="mb-3",
            ),  
        ])
    elif tab == 'tab-2':

        df = fetch_history()

        if df.empty:
            sensor_columns = []
        else:
            sensor_columns = [c for c in df.columns if c != "time"]
            
        sensor_columns = [c for c in df.columns if c != "time"]

        return html.Div([

            dcc.Dropdown(
                id="sensor-filter",
                options=[{"label": s, "value": s} for s in sensor_columns],
                value=sensor_columns,   # all selected initially
                multi=True,
                placeholder="Select sensors"
            ),

            dash_ag_grid.AgGrid(
                id="history-table",
                rowData=df.to_dict("records"),
                columnDefs=[{"field": i} for i in df.columns],
                defaultColDef={"Autosize":True,},
                dashGridOptions={"pagination": True, "paginationAutoPageSize": True},
                # style_cell={'textAlign': 'center'},
                # page_size=10,
                # sort_action="native",
            ),
        ])
    
@app.callback(
    Output("latest-table", "data"),
    Input("interval-component", "n_intervals")
)
def update_latest(n):
    df = fetch_history()

    if df.empty:
        return []

    latest = df.sort_values("time", ascending=False).head(1)

    return latest.to_dict("records")

@app.callback(
    Output("history-table", "data"),
    Output("history-table", "columns"),
    Input("sensor-filter", "value")
)
def update_history(selected_sensors):

    df = fetch_history()

    if df.empty:
        return [], []

    if not selected_sensors:
        return [], []

    columns_to_show = ["time"] + selected_sensors
    df_filtered = df[columns_to_show]

    return (
        df_filtered.to_dict("records"),
        [{"name": i, "id": i} for i in df_filtered.columns]
    )

if __name__ == '__main__':
   app.run(host="localhost", port=8050, debug=True)