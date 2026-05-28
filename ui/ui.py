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
        html.P(
            children=[
                html.Div(
                    children=[
                        html.H2("Optimal Settings"),
                    ],
                    className= "blue-box"
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
                    className="box center-vertical"
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
                )
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
        df = fetch_history()
    
        latest = df.sort_values("time", ascending=False).head(1)
        print(latest.get("ambient_temp")[0])


        return html.Div(
            [

             #html.H4("Latest Temperature & Humidity"),
             #Table to display latest reading
               dash_ag_grid.AgGrid(
                    id="latest-table",  
                    rowData=latest.to_dict("records"),
                    columnDefs=[{"field": i} for i in df.columns],
                    defaultColDef ={
                        "resizable": True,
                        "cellStyle": {"wordBreak": "normal"},
                        "autoHeaderHeight": True,
                    },

                    dashGridOptions={"theme": 
                                 {"function": "themeBalham.withParams({ "
                                 "backgroundColor: 'white', "
                                 "headerTextColor: 'white', "
                                 "headerBackgroundColor: 'steelBlue',"
                                 "headerFontSize: 14,"
                                 "headerVerticalPaddingScale: 0.5,"
                                 "headerHorizontalPaddingScale: 0.5,"
                                 "spacing: 10 })"}}


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