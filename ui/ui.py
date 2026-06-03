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
                        html.P(children="Fan Speed Level"),
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
                        html.P(children=" Water Chiller Temp ℃"),
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
                        html.P("Total Water Collected"),
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
                        html.P(children="Fan Speed Level"),
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
                        html.P(children="Water Chiller Temperature ℃"),
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
                        html.P("Optimal Water Flow Rate"),
                        html.P("0 mL/hr"),
                    ],
                    className= "box center-vertical",
                    style={ "height":"35%"}
                ),
                html.Div(
                    children=[
                        html.P("Optimal Power Usage"),
                        html.P("10 Watts"),
                    ],
                    className= "box center-vertical",
                    style={ "height":"25%"}
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
        print(df.columns)

        ambient_temp = [
            dbc.CardHeader("Temp Inside"),
            dbc.CardBody(
                [
                    html.P(
                        latest.get("ambient_temp"),
                        className="card-text",
                    ),
                ]
            ),
        ]
        ambient_temp_outside = [
            dbc.CardHeader("Ambient Temp"),
            dbc.CardBody(
                [
                    html.P(
                        latest.get("ambient_temp_outside"),
                        className="card-text",
                    ),
                ]
            ),
        ]
        apower_1 = [
            dbc.CardHeader("Water Chiller Power"),
            dbc.CardBody(
                [
                    html.P(
                        latest.get("apower_1"),
                        className="card-text",
                    ),
                ]
            ),
        ]
        apower_2 = [
            dbc.CardHeader("Fan Power"),
            dbc.CardBody(
                [
                    html.P(
                        latest.get("apower_2"),
                        className="card-text",
                    ),
                ]
            ),
        ]
        power_total = [
            dbc.CardHeader("Total Fan Power"),
            dbc.CardBody(
                [
                    html.P(
                        latest.get("apower_2"),
                        className="card-text",
                    ),
                ]
            ),
        ]
        
        total_power = [
            dbc.CardHeader("Total Power"),
            dbc.CardBody(
                [
                    html.P(
                        latest.get("apower_2"),
                        className="card-text",
                    ),
                ]
            ),
        ]
        chiller_temp = [
            dbc.CardHeader("Ambient Temperature"),
            dbc.CardBody(
                [
                    html.P(
                        latest.get("chiller_temp"),
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
                        latest.get("coil_temp_bot"),
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
                        latest.get("coil_temp_mid"),
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
                        latest.get("coil_temp_top"),
                        className="card-text",
                    ),
                ]
            ),
        ]
        current_weight = [
            dbc.CardHeader("Ambient Temperature"),
            dbc.CardBody(
                [
                    html.P(
                        latest.get("current_weight"),
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
                        latest.get("dew_point_inside"),
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
                        latest.get("dew_point_outside"),
                        className="card-text",
                    ),
                ]
            ),
        ]
        fan_speed = [
            dbc.CardHeader("Ambient Temp"),
            dbc.CardBody(
                [
                    html.P(
                        latest.get("fan_speed"),
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
                        latest.get("humidity"),
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
                        latest.get("humidity_outside"),
                        className="card-text",
                    ),
                ]
            ),
        ]
        water_rate_ml_hr = [
            dbc.CardHeader("Water Production Rate (ml/hr)"),
            dbc.CardBody(
                [
                    html.P(
                        latest.get("water_rate_ml_hr"),
                        className="card-text",
                    ),
                ]
            ),
        ]

        return html.Div([
                    
            dbc.Row(
                [
                    
                    dbc.Col(dbc.Card(ambient_temp_outside, color="#00628e", inverse=True)),
                    dbc.Col(dbc.Card(humidity_outside, color="#49abc8", inverse=True)),
                    dbc.Col(dbc.Card(dew_point_outside, color="#266774", inverse=True)),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(dbc.Card(ambient_temp, color="#00628e", inverse=True)),
                    dbc.Col(dbc.Card(humidity, color="#49abc8", inverse=True)),
                    dbc.Col(dbc.Card(dew_point_inside, color="#266774", inverse=True)),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(dbc.Card(coil_temp_top, color="#00364D", inverse=True)),
                    dbc.Col(dbc.Card(coil_temp_mid, color="#00364D", inverse=True)),
                    dbc.Col(dbc.Card(coil_temp_bot, color="#00364D", inverse=True)),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(dbc.Card(apower_1, color="#aed0d6" )),
                    dbc.Col(dbc.Card(apower_2, color="#aed0d6")),
                ],
                className="mb-4",
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