from dash import Dash, dcc, html, dash_table, Input, Output, callback
import dash_daq as daq
import pandas as pd
import requests


API_URL_SENSORS = "http://api:5001/read-sensors"
API_URL_HISTORY = "http://api:5001/data"

external_stylesheets = [
    {
        "href": "/assets/style.css",
        "rel": "stylesheet",
    },
]

app = Dash(
    __name__,
    external_stylesheets=external_stylesheets,
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
                        html.P(children="Fan Speed"),
                        daq.Gauge(
                            min=0,
                            max=20,
                            value=15,
                            size=150,
                            units='mph',
                            showCurrentValue=True
                        )
                    ],
                    className="fan-speed box center-vertical"
                ),
                html.Div(
                    children=[
                        html.P(children="Chiller Temp"),
                        daq.Thermometer(
                            value=20,
                            max=35,
                            min=5,
                            units="C",
                            height=120,
                            showCurrentValue=True
                        )  
                    ],
                    className="chiller-temp box center-vertical"
                ),
                html.Div(
                    children=[
                        html.P("Water Collected"),
                        daq.Tank(
                        id="progress-gauge",
                        color="#86D1FF",
                        height=150,
                        units="Liters",
                        value=3,
                        max=5,
                        min=0,
                        showCurrentValue=True,  # default size 200 pixel
                        ),
                    ],
                    className= "water-collection box center-vertical"
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
                    className="box"
                ),
            className="header-center",
        ),

        # Right Div
        html.P(
            children=[
                html.Div(
                    children=[
                        html.H2("Optimal Water Generation"),
                    ],
                    className="box"
                ),

                html.Div(
                    children=[
                        html.P(children="Fan Speed"),
                        html.P(children="20"),
                        html.P(children="mph")
                    ],
                    className="fan-speed-right box center-vertical"
                ),
                html.Div(
                    children=[
                        html.P(children="Water Chiller Temperature"),
                        html.P(children="5C"),
                    ],
                    className="water-chiller-temp box center-vertical"
                ),
                html.Div(
                    children=[
                        html.P(children="Water Chiller Flow Rate"),
                        html.P(children="22"),
                        html.P(children="mph")
                    ],
                    className="water-chiller-flow-rate box center-vertical"
                ),
            ],
            className="header-right",
        ),
        
    ],
    className="header",
    style={
        "minHeight": "100vh",  # full viewport height
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
        return html.Div([
            # html.H1("Latest Temperature & Humidity"),

            # Table to display latest reading
            dash_table.DataTable(
                id="latest-table",
                style_table={
                    'width': '100%',
                    'overflowX': 'auto',
                },
                style_cell={
                    'textAlign': 'center',
                    'whiteSpace': 'normal',
                    'height': 'auto',
                    'color': 'black',
                    'backgroundColor': 'white',
                },
                style_header={
                    'color': 'black',
                    'backgroundColor': '#f0f0f0',
                    'fontWeight': 'bold'
                },
                page_size=10,
                sort_action="native",
            ),

            # Auto-refresh every 5 seconds
            dcc.Interval(
                id='interval-component',
                interval=5*1000,  # milliseconds
                n_intervals=0
            )
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

            dash_table.DataTable(
                id="history-table",
                style_cell={'textAlign': 'center'},
                page_size=10,
                sort_action="native",
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
   app.run(host="0.0.0.0", port=8050, debug=True)