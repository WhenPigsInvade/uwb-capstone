from dash import Dash, dcc, html, dash_table, Input, Output, State, callback
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
    suppress_callback_exceptions=True  
)

app.title = "Exawater"

app.layout = html.Div(
    children=[
        # ✅ Added Interval component (60,000 ms = 1 minute)
        dcc.Interval(
            id='interval-component',
            interval=60*1000, 
            n_intervals=0
        ),
        
        # ✅ Added a dcc.Store to cache the projected values between the 20-minute updates
        dcc.Store(id='projected-store', data={'water': 'N/A mL/hr', 'power': '0 kWh'}),

        # Left Div
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
                            showCurrentValue=True,  
                        ),
                    ],
                    className= "water-collection box"
                ),
            ],
            className="header-left"
        ),

        # Center Div
        html.Div(
            children=[
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
                )
            ],
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
                        html.P("Optimized Water Flow Rate"), 
                        html.P(" mL/hr"),
                    ],
                    className= "box center-vertical",
                    style={ "height":"35%"}
                ),
                html.Div(
                    children=[
                        html.P("Optimized Power Usage"), 
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
        "minHeight": "99vh", 
        "display": "flex",
        "flexDirection": "row",
        "alignItems": "flex-start", 
        "backgroundColor": "#1e2130",
        "margin" : "0px" 
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
    Output('projected-store', 'data'), # ✅ Send updated cache back to store
    Input('tabs-example-1', 'value'),
    Input('interval-component', 'n_intervals'),
    State('projected-store', 'data') # ✅ Grab the current cache state
) 
def render_content(tab, n_intervals, store_data):
    
    # Initialize store if None (on very first startup)
    if store_data is None:
        store_data = {'water': 'N/A mL/hr', 'power': '0 kWh'}
    
    if tab == 'tab-1':
        df = fetch_history()
        
        if df.empty:
            return html.Div("No data available yet.", style={"color": "white"}), store_data
    
        latest = df.sort_values("time", ascending=False).head(1)
        
        # Guard in case columns don't exist yet
        try:
            power_total = latest.get("apower_1", pd.Series([0])) + latest.get("apower_2", pd.Series([0]))
            power_total = round(power_total, 2)
        except Exception:
            power_total = pd.Series([0])

        def get_val(col_name, unit=""):
            val = latest.get(col_name)
            if val is not None and not val.empty:
                return f"{val.item()} {unit}"
            return f"N/A {unit}"

        # ✅ Check if 20 minutes have passed (or if this is the initial layout loading)
        # n_intervals increments once per minute, so modulo 20 traps every 20th minute.
        if n_intervals == 0 or n_intervals % 20 == 0:
            store_data['water'] = get_val('water_rate_ml_hr', 'mL/hr')
            store_data['power'] = f"{power_total.item()} kWh"

        # Cleaned up card generation using a helper to avoid dictionary lookup errors
        ambient_temp = [dbc.CardHeader("Inside Temp"), dbc.CardBody([html.P(get_val('ambient_temp', '℃'), className="card-text")])]
        ambient_temp_outside = [dbc.CardHeader("Ambient Temp"), dbc.CardBody([html.P(get_val('ambient_temp_outside', '℃'), className="card-text")])]
        coil_temp_bot = [dbc.CardHeader("Inlet Coil Temp"), dbc.CardBody([html.P(get_val('coil_temp_bot', '℃'), className="card-text")])]
        coil_temp_mid = [dbc.CardHeader("Mid Coil Temp"), dbc.CardBody([html.P(get_val('coil_temp_mid', '℃'), className="card-text")])]
        coil_temp_top = [dbc.CardHeader("Outlet Coil Temp"), dbc.CardBody([html.P(get_val('coil_temp_top', '℃'), className="card-text")])]
        dew_point_inside = [dbc.CardHeader("Inside Dew Point"), dbc.CardBody([html.P(get_val('dew_point_inside', '℃'), className="card-text")])]
        dew_point_outside = [dbc.CardHeader("Ambient Dew Point"), dbc.CardBody([html.P(get_val('dew_point_outside', '℃'), className="card-text")])]
        humidity = [dbc.CardHeader("Inside Humidity"), dbc.CardBody([html.P(get_val('humidity', '%'), className="card-text")])]
        humidity_outside = [dbc.CardHeader("Ambient Humidity"), dbc.CardBody([html.P(get_val('humidity_outside', '%'), className="card-text")])]
        water_rate_ml_hr = [dbc.CardHeader("Water Production Rate"), dbc.CardBody([html.P(get_val('water_rate_ml_hr', 'mL/hr'), className="card-text")])]
        
        total_power = [
            dbc.CardHeader("Total Power Usage"),
            dbc.CardBody([html.P(f"{power_total.item()} kWh", className="card-text")])
        ]
        
        # ✅ Load the 20-minute values directly from the cache
        proj_water_rate = [
            dbc.CardHeader("Projected Water Production Rate"),
            dbc.CardBody([html.P(store_data['water'], className="card-text")])
        ]
        proj_total_power = [
            dbc.CardHeader("Projected Total Power Usage"),
            dbc.CardBody([html.P(store_data['power'], className="card-text")])
        ]

        layout = html.Div([
            dbc.Row([
                dbc.Col(dbc.Card(ambient_temp_outside, color="#00628e", inverse=True, style={"font-size": 20})),
                dbc.Col(dbc.Card(humidity_outside, color="#49abc8", inverse=True, style={"font-size": 20})),
                dbc.Col(dbc.Card(dew_point_outside, color="#266774", inverse=True, style={"font-size": 20})),
            ], className="mb-3"),
            dbc.Row([
                dbc.Col(dbc.Card(ambient_temp, color="#00628e", inverse=True, style={"font-size": 20})),
                dbc.Col(dbc.Card(humidity, color="#49abc8", inverse=True, style={"font-size": 20})),
                dbc.Col(dbc.Card(dew_point_inside, color="#266774", inverse=True, style={"font-size": 20})),
            ], className="mb-3"),
            dbc.Row([
                dbc.Col(dbc.Card(coil_temp_top, color="#00364D", inverse=True, style={"font-size": 20})),
                dbc.Col(dbc.Card(coil_temp_mid, color="#00364D", inverse=True, style={"font-size": 20})),
                dbc.Col(dbc.Card(coil_temp_bot, color="#00364D", inverse=True, style={"font-size": 20})),
            ], className="mb-3"),
            dbc.Row([
                dbc.Col(dbc.Card(water_rate_ml_hr, color="#aed0d6", style={"font-size": 20})),
                dbc.Col(dbc.Card(total_power, color="#aed0d6", style={"font-size": 20})),
            ], className="mb-3"),
            dbc.Row([
                dbc.Col(dbc.Card(proj_water_rate, color="white", style={"font-size": 20}, className="border border-info border-4")),
                dbc.Col(dbc.Card(proj_total_power, color="white", style={"font-size": 20}, className="border border-info border-4")),
            ], className="mb-3"),  
        ])
        
        # ✅ Must return tuple because we have two Outputs now
        return layout, store_data
        
    elif tab == 'tab-2':
        df = fetch_history()

        if df.empty:
            sensor_columns = []
            records = []
            cols = []
        else:
            sensor_columns = [c for c in df.columns if c != "time"]
            records = df.to_dict("records")
            cols = [{"field": i} for i in df.columns]

        layout = html.Div([
            dcc.Dropdown(
                id="sensor-filter",
                options=[{"label": s, "value": s} for s in sensor_columns],
                value=sensor_columns,   # all selected initially
                multi=True,
                placeholder="Select sensors"
            ),

            dash_ag_grid.AgGrid(
                id="history-table",
                rowData=records,
                columnDefs=cols,
                defaultColDef={"autosize": True}, 
                dashGridOptions={"pagination": True, "paginationAutoPageSize": True},
            ),
        ])
        
        # ✅ Return tuple here too to maintain the cache
        return layout, store_data

@callback(
    Output("latest-table", "data"),
    Input("interval-component", "n_intervals")
)
def update_latest(n_intervals):
    df = fetch_history()

    if df.empty:
        return []

    latest = df.sort_values("time", ascending=False).head(1)
    return latest.to_dict("records")

@callback(
    Output("history-table", "rowData"),
    Output("history-table", "columnDefs"),
    Input("sensor-filter", "value"),
    Input("interval-component", "n_intervals") 
)
def update_history(selected_sensors, n_intervals):

    df = fetch_history()

    if df.empty or not selected_sensors:
        return [], []

    columns_to_show = ["time"] + selected_sensors
    
    # Filter only columns that actually exist in the dataframe
    columns_to_show = [c for c in columns_to_show if c in df.columns]
    df_filtered = df[columns_to_show]

    return (
        df_filtered.to_dict("records"),
        [{"field": i} for i in df_filtered.columns] 
    )

if __name__ == '__main__':
    app.run(host="localhost", port=8050, debug=True)