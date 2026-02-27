from dash import Dash, dcc, html, dash_table, Input, Output, callback
import pandas as pd
import requests


API_URL = "http://localhost:420/read-sensors"

app = Dash()

external_stylesheets = [
    {
        "href": (
            "/assets/style.css"
        ),
        "rel": "stylesheet",
    },
]
app = Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "Exawater"

df = pd.read_csv('data/data.csv')

app.layout = html.Div(
    children=[
    
        html.Div(
            children=[
                html.Div(
                    children=[
                        html.P(children="Fan Speed"),
                        html.P(children="20"),
                        html.P(children="mph")
                    ],
                    className="fan-speed box center-vertical"
                ),
                html.Div(
                    children=[
                        html.P(children="Water Collection"),
                        html.P(children="*insert fancy graphic here*"),
                    ],
                    className="water-collection box center-vertical"
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
        "backgroundColor": "#f0f0f0",
        "margins" : "0px"
    }

)

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
                id='sensor-table',
                columns=[
                    {"name": "Temperature (°C)", "id": "temperature"},
                    {"name": "Humidity (%)", "id": "humidity"}
                ],
                style_table={'width': '100%'},
                style_cell={
                    'textAlign': 'center',
                    'width': '50%',
                    'minWidth': '50%',
                    'maxWidth': '50%',
                }
            ),

            # Auto-refresh every 5 seconds
            dcc.Interval(
                id='interval-component',
                interval=5*1000,  # milliseconds
                n_intervals=0
            )
        ])
    elif tab == 'tab-2':
        return html.Div([
            # html.H3('Tab content 2'),
            dash_table.DataTable(df.to_dict('records'), [{"name": i, "id": i} for i in df.columns],
            style_cell={'textAlign': 'left'}
                                 ),
        ])
    

@app.callback(
    Output('sensor-table', 'data'),
    Input('interval-component', 'n_intervals')
)
def update_data(n):
    try:
        # Fetch data from API
        response = requests.get(API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()

        # Expecting JSON like: {"temperature": 23.5, "humidity": 60}
        temperature = data.get("temperature")
        humidity = data.get("humidity")

        # Return as table row
        return [{"temperature": temperature, "humidity": humidity}]

    except (requests.RequestException, KeyError, ValueError) as e:
        # Show error in table
        return [{"temperature": "Error", "humidity": "Error"}]

if __name__ == '__main__':
   app.run(debug=True)