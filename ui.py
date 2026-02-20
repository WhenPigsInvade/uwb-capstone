from dash import Dash, dcc, html, dash_table, Input, Output, callback
import pandas as pd

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
                    className="fan-speed, box"
                ),
                html.Div(
                    children=[
                        html.P(children="Water Collection"),
                        html.P(children="*insert fancy graphic here*"),
                    ],
                    className="water-collection, box"
                ),
            ],
            className="header-left"
        ),

        html.Div(
            children = 
                html.Div(
                    children=[
                        html.P(children="Current System Metrics"),

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

        html.P(
            children=(
                "Right"
            ),
            className="header-right",
        ),
        
    ],
    className="header"
)

@callback(
    Output('tabs-example-content-1', 'children'),
    Input('tabs-example-1', 'value')
)
def render_content(tab):
    if tab == 'tab-1':
        return html.Div([
            html.H3('Tab content 1'),
            dcc.Graph(
                figure=dict(
                    data=[dict(
                        x=[1, 2, 3],
                        y=[3, 1, 2],
                        type='bar'
                    )]
                )
            )
        ])
    elif tab == 'tab-2':
        return html.Div([
            html.H3('Tab content 2'),
            dash_table.DataTable(df.to_dict('records'), [{"name": i, "id": i} for i in df.columns]),
        ])


if __name__ == '__main__':
   app.run(debug=True)