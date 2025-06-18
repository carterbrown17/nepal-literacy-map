import json
import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html, Input, Output

# Load Out-of-School Rate (OOS) data for Nepal from UIS
df_oos_raw = pd.read_csv("data/OOS_Rate_Countries.csv")
df_oos_raw.columns = df_oos_raw.columns.str.strip().str.lower()

df_oos_nepal = df_oos_raw[
    (
        (df_oos_raw["country"].str.strip().str.upper() == "NPL") |
        (df_oos_raw["name"].str.strip().str.lower() == "nepal")
    ) &
    (df_oos_raw["level"].str.strip().str.lower().isin(["prim", "lsec", "usec"])) &
    (df_oos_raw["value"].notna())
][["year", "value", "sex", "level"]].copy()

df_oos_nepal["Level"] = df_oos_nepal["level"].map({
    "prim": "Primary",
    "lsec": "Lower Secondary",
    "usec": "Upper Secondary"
})
df_oos_nepal["Level"] = df_oos_nepal["Level"].str.title()
df_oos_nepal.rename(columns={"year": "Year", "value": "value", "sex": "Gender"}, inplace=True)
df_oos_nepal["Gender"] = df_oos_nepal["Gender"].str.strip().str.lower().map({
    "mf": "Total", "m": "Male", "f": "Female",
    "male": "Male", "female": "Female", "total": "Total"
})
df_oos_nepal["indicator"] = df_oos_nepal["Level"].map({
    "Primary": "OOS.1",
    "Lower Secondary": "OOS.2",
    "Upper Secondary": "OOS.3"
})

# Load GeoJSON
with open("data/nepal-with-provinces-acesmndr.geojson", "r", encoding="utf-8") as f:
    geojson = json.load(f)

# Map internal names to official province names
province_name_map = {
    "Province No. 1": "Koshi",
    "Province No. 2": "Madhesh",
    "Province No. 3": "Bagmati",
    "Province No. 4": "Gandaki",
    "Province No. 5": "Lumbini",
    "Province No. 6": "Karnali",
    "Province No. 7": "Sudurpashchim"
}

for feature in geojson["features"]:
    old_name = feature["properties"]["name"]
    if old_name in province_name_map:
        feature["properties"]["ADM1_EN"] = province_name_map[old_name]
    else:
        # If the name is already a proper province name, use it directly
        feature["properties"]["ADM1_EN"] = old_name

# Load literacy data
df = pd.read_csv("data/table-6.1-literacy-rates-by-sex-percent.csv")
df_clean = df.iloc[3:10, [0, 1, 2, 3]]
df_clean.columns = ["Province", "Male", "Female", "Total"]
df_clean["Total"] = pd.to_numeric(df_clean["Total"], errors="coerce")
# Standardize province name in df_clean to match GeoJSON
df_clean["Province"] = df_clean["Province"].replace({
    "Sudur Pashchim": "Sudurpashchim",
    "Sudurpaschim": "Sudurpashchim"
})

# Load and clean additional datasets
df_6_2 = pd.read_csv("data/table-6.2-literacy-rates-by-age-group-sex-and-urban_rural-area-percent.csv", skiprows=1)
df_6_3 = pd.read_csv("data/6.3-literacy-rates-in-nepal-by-age-group-sex-and-poverty-status-percent.csv", skiprows=1)

df_6_2.columns = df_6_2.columns.str.strip()
df_6_3.columns = df_6_3.columns.str.strip()

df_13_raw = pd.read_csv("data/individual-table-13-population-aged-5-years-and-above-by-literacy-status-by-province.csv", header=None)
df_13_raw.columns = df_13_raw.iloc[0]  # First row becomes header
df_13 = df_13_raw[1:].copy()  # Drop the first row now that it's the header
df_13.rename(columns={df_13.columns[0]: "Province"}, inplace=True)
df_13.columns = df_13.columns.str.strip()

# Weighted literacy analysis (normalized illiteracy rate by province)
df_13_weighted = df_13.iloc[1:].copy()
df_13_weighted.rename(columns={df_13_weighted.columns[0]: "Province"}, inplace=True)

total_col = "Population aged 5 years & above"
cannot_read_col = "Can't read & write"

df_13_weighted["Total Population"] = pd.to_numeric(df_13_weighted[total_col], errors="coerce")
df_13_weighted["Cannot Read and Write"] = pd.to_numeric(df_13_weighted[cannot_read_col], errors="coerce")


# Normalize illiteracy by population
df_13_weighted["Normalized Illiteracy Rate (%)"] = (
    df_13_weighted["Cannot Read and Write"] / df_13_weighted["Total Population"] * 100
)

# Drop rows with missing data
df_13_weighted.dropna(subset=["Province", "Normalized Illiteracy Rate (%)"], inplace=True)

df_14 = pd.read_csv("data/individual-table-14-population-aged-5-years-and-above-by-educational-attainment.csv", skiprows=1)
df_14.rename(columns={df_14.columns[0]: "Province"}, inplace=True)
df_14.columns = df_14.columns.str.strip()

 # df_ofst is deprecated and replaced by df_oos_nepal
 # Load NER and GER datasets from Excel with correct header assignment (row 0 as header, data starts from row 1)
df_ner_raw = pd.read_excel("data/table-6.11_NER Nepal Living Standards Survey IV 2023.xlsx", sheet_name="NER Data", header=None)
df_ner_raw.columns = df_ner_raw.iloc[0]  # Assign row 0 as header
df_ner_raw = df_ner_raw[1:].copy()
df_ner_raw.columns = df_ner_raw.columns.str.strip()

df_ger_raw = pd.read_excel("data/table-6.11_NER Nepal Living Standards Survey IV 2023.xlsx", sheet_name="GER Data", header=None)
df_ger_raw.columns = df_ger_raw.iloc[0]
df_ger_raw = df_ger_raw[1:].copy()
df_ger_raw.columns = df_ger_raw.columns.str.strip()

df_ner = df_ner_raw.copy()
df_ger = df_ger_raw.copy()

df_ner.rename(columns={df_ner.columns[0]: "Category", df_ner.columns[1]: "Region"}, inplace=True)
df_ger.rename(columns={df_ger.columns[0]: "Category", df_ger.columns[1]: "Region"}, inplace=True)

ner_provinces = df_ner[df_ner["Category"] == "Province"]
ger_provinces = df_ger[df_ger["Category"] == "Province"]

# Load GER Time Series datasets
df_ger2 = pd.read_csv("data/gdata2.csv")
df_ger2.columns = df_ger2.columns.str.strip()
df_ger3 = pd.read_csv("data/gdata3.csv")
df_ger3.columns = df_ger3.columns.str.strip()

df_ger_time = pd.concat([df_ger2, df_ger3], ignore_index=True)

# Map Level based on indicatorId prefix
def map_level(indicator):
    if isinstance(indicator, str):
        if indicator.startswith("GER.1"):
            return "Primary"
        elif indicator.startswith("GER.2"):
            return "Lower Secondary"
        elif indicator.startswith("GER.3"):
            return "Upper Secondary"
    return None

df_ger_time["Level"] = df_ger_time["indicatorId"].apply(map_level)
# Standardize column names and ensure "Year" is properly recognized
df_ger_time.columns = df_ger_time.columns.str.strip()
df_ger_time.rename(columns=lambda x: str(x).strip(), inplace=True)
if "year" in df_ger_time.columns:
    df_ger_time.rename(columns={"year": "Year"}, inplace=True)
df_ger_time["indicator"] = df_ger_time["Level"].map({
    "Primary": "GER.1",
    "Lower Secondary": "GER.2",
    "Upper Secondary": "GER.3"
})
# Add Gender and Source columns after indicator is created
df_ger_time["Gender"] = df_ger_time["indicatorId"].apply(lambda x: "Male" if ".M" in x else "Female" if ".F" in x else "Total")

# Load NER Time Series datasets
df_ner1 = pd.read_csv("data/ndata1.csv")
df_ner2 = pd.read_csv("data/ndata2.csv")

df_ner1.columns = df_ner1.columns.str.strip()
df_ner2.columns = df_ner2.columns.str.strip()

df_ner_time = pd.concat([df_ner1, df_ner2], ignore_index=True)

def map_ner_level(indicator):
    if isinstance(indicator, str):
        if "NERT.1" in indicator:
            return "Primary"
        elif "NERT.2" in indicator:
            return "Lower Secondary"
        elif "NERT.3" in indicator:
            return "Upper Secondary"
    return None

df_ner_time["Level"] = df_ner_time["indicatorId"].apply(map_ner_level)
df_ner_time.columns = df_ner_time.columns.str.strip()
df_ner_time.rename(columns=lambda x: str(x).strip(), inplace=True)
if "year" in df_ner_time.columns:
    df_ner_time.rename(columns={"year": "Year"}, inplace=True)
# indicator assignment: map Level to NER.1, NER.2, NER.3
df_ner_time["indicator"] = df_ner_time["Level"].map({
    "Primary": "NER.1",
    "Lower Secondary": "NER.2",
    "Upper Secondary": "NER.3"
})
df_ner_time["Gender"] = df_ner_time["indicatorId"].apply(lambda x: "Male" if ".M" in x else "Female" if ".F" in x else "Total")




# Create Dash app
app = dash.Dash(__name__)
app.title = "Nepal Literacy Rates"

# Add dataset dropdown above map + sidebar
app.layout = html.Div([
    html.H1("Nepal Literacy Map", style={"textAlign": "center"}),

    html.Div([
        html.Label("Select Dataset:", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id="dataset-selector",
            options=[
                {"label": "Literacy by Province (6.1)", "value": "table_6_1"},
                {"label": "Literacy by Age & Urban/Rural (6.2)", "value": "table_6_2"},
                {"label": "Literacy by Age & Poverty (6.3)", "value": "table_6_3"},
                {"label": "Literacy Status by Province (Table 13)", "value": "table_13"},
                {"label": "Normalized Illiteracy Rate", "value": "table_13_weighted"},
                {"label": "Educational Attainment (Table 14)", "value": "table_14"},
                {"label": "Net Enrollment Rate (NER)", "value": "ner"},
                {"label": "Gross Enrollment Rate (GER)", "value": "ger"},
                {"label": "Out-of-School Rate (OOS)", "value": "oos"},
                {"label": "GER, NER, OOS (Time Series)", "value": "ger_time"},
            ],
            value="table_6_1",
            clearable=False,
            style={"width": "50%", "marginBottom": "20px"}
        )
    ], style={"padding": "0 30px"}),


    html.Div([
        dcc.Graph(id="map", style={"height": "80vh", "width": "70vw"}),
        html.Div(
            id="info-box",
            children=[
                html.Div(id="province-data", style={"marginBottom": "20px"}),
                html.Div(id="indicator-wrapper", children=[
                    html.Label("Select Indicator:", style={"fontWeight": "bold"}),
                    dcc.Dropdown(
                        id="indicator-selector",
                        options=[],
                        value=None,
                        clearable=False,
                        style={"width": "100%", "marginBottom": "20px"}
                    ),
                ], style={"display": "none"}),

                html.Div(id="viewmode-wrapper", children=[
                    html.Label("Select View Mode (6.3 only):", style={"fontWeight": "bold"}),
                    dcc.Dropdown(
                        id="view-selector",
                        options=[
                            {"label": "Split by Poverty Group", "value": "split"},
                            {"label": "Combined View", "value": "combined"}
                        ],
                        value="split",
                        clearable=False,
                        style={"width": "100%", "marginBottom": "20px"}
                    ),
                ], style={"display": "none"}),

                html.Div(
                    id="sidebar-chart-wrapper",
                    children=[
                        dcc.Graph(id="sidebar-chart")
                    ]
                )
            ],
            style={
                "padding": "20px",
                "fontSize": "16px",
                "width": "25vw",
                "height": "80vh",
                "overflowY": "auto",
                "display": "inline-block",
                "verticalAlign": "top",
                "borderLeft": "2px solid #ccc",
                "backgroundColor": "#f9f9f9"
            }
        ),
    ], style={"display": "flex", "justifyContent": "space-between"})
])

# Callback for indicator dropdown options, default value, and visibility of dropdown wrappers and sidebar chart
@app.callback(
    Output("indicator-selector", "options"),
    Output("indicator-selector", "value"),
    Output("indicator-wrapper", "style"),
    Output("viewmode-wrapper", "style"),
    Output("sidebar-chart-wrapper", "style"),
    Input("dataset-selector", "value")
)
def update_indicator_dropdown(dataset):
    if dataset == "table_13":
        valid_columns = [col for col in df_13.columns[1:] if col and col != "Category"]
        options = [{"label": col, "value": col} for col in valid_columns if pd.notna(col)]
        if options:
            return options, options[0]["value"], {"display": "block"}, {"display": "none"}, {"display": "block"}
        else:
            return [], None, {"display": "block"}, {"display": "none"}, {"display": "block"}
    elif dataset == "table_14":
        options = [{"label": col, "value": col} for col in df_14.columns[1:] if pd.notna(col)]
        if options:
            return options, options[0]["value"], {"display": "block"}, {"display": "none"}, {"display": "block"}
        else:
            return [], None, {"display": "block"}, {"display": "none"}, {"display": "block"}
    elif dataset == "ner":
        indicator_options = [{"label": col, "value": col} for col in df_ner.columns[2:] if pd.notna(col)]
        if indicator_options:
            return indicator_options, indicator_options[0]["value"], {"display": "block"}, {"display": "none"}, {"display": "block"}
        else:
            return [], None, {"display": "block"}, {"display": "none"}, {"display": "block"}
    elif dataset == "ger":
        indicator_options = [{"label": col, "value": col} for col in df_ger.columns[2:] if pd.notna(col)]
        if indicator_options:
            return indicator_options, indicator_options[0]["value"], {"display": "block"}, {"display": "none"}, {"display": "block"}
        else:
            return [], None, {"display": "block"}, {"display": "none"}, {"display": "block"}
    elif dataset == "ger_time":
        # Group indicators by Level for GER time series
        options = [
            {"label": "Primary Education", "value": "GER.1"},
            {"label": "Lower Secondary Education", "value": "GER.2"},
            {"label": "Upper Secondary Education", "value": "GER.3"}
        ]
        return options, "GER.1", {"display": "block"}, {"display": "none"}, {"display": "none"}
    elif dataset == "table_6_3":
        return [], None, {"display": "none"}, {"display": "block"}, {"display": "none"}
    elif dataset == "table_6_2":
        return [], None, {"display": "none"}, {"display": "none"}, {"display": "none"}
    elif dataset == "oos":
        # More descriptive labels for OOS indicators, including 'All Levels'
        indicator_labels = {
            "OOS.1": "Primary Out-Of-School Rate (%)",
            "OOS.2": "Lower Secondary Out-Of-School Rate (%)",
            "OOS.3": "Upper Secondary Out-Of-School Rate (%)",
            "all": "All Levels"
        }
        options = [{"label": label, "value": key} for key, label in indicator_labels.items()]
        if options:
            return options, options[0]["value"], {"display": "block"}, {"display": "none"}, {"display": "none"}
        else:
            return [], None, {"display": "block"}, {"display": "none"}, {"display": "none"}
    else:
        return [], None, {"display": "none"}, {"display": "none"}, {"display": "block"}

# Dataset switching logic with conditional rendering for bar charts and view modes, and map coloring for 13/14
@app.callback(
    Output("map", "figure"),
    Input("dataset-selector", "value"),
    Input("view-selector", "value"),
    Input("indicator-selector", "value")
)
def update_map(dataset, view_mode, indicator):
    import plotly.graph_objs as go
    if dataset == "table_6_1":
        return px.choropleth_mapbox(
            df_clean,
            geojson=geojson,
            locations="Province",
            featureidkey="properties.ADM1_EN",
            color="Total",
            color_continuous_scale="YlGnBu",
            mapbox_style="carto-positron",
            zoom=5.5,
            center={"lat": 28.3949, "lon": 84.1240},
            opacity=0.7,
            hover_name="Province",
            hover_data={"Total": True, "Male": True, "Female": True, "Province": False}
        )
    elif dataset == "table_6_2":
        df_6_2_long = df_6_2.melt(id_vars="Age group", value_vars=["Total in urban", "Total in Rural"],
                                  var_name="Area", value_name="Literacy Rate (%)")
        df_6_2_long["Area"] = df_6_2_long["Area"].replace({
            "Total in urban": "Urban",
            "Total in Rural": "Rural"
        })
        fig_6_2 = px.bar(
            df_6_2_long,
            x="Age group",
            y="Literacy Rate (%)",
            color="Area",
            barmode="group",
            title="Literacy by Age Group and Area Type",
        )
        fig_6_2.update_layout(height=600)
        return fig_6_2
    elif dataset == "table_6_3":
        df_6_3_fixed = df_6_3.copy()
        df_6_3_fixed.set_index("Gender/Poverty Status", inplace=True)
        df_6_3_fixed = df_6_3_fixed.drop(columns=["Total"], errors="ignore").T
        df_6_3_fixed.reset_index(inplace=True)
        df_6_3_fixed = df_6_3_fixed.rename(columns={"index": "Age group"})

        df_6_3_long = df_6_3_fixed.melt(id_vars="Age group", var_name="Status", value_name="Literacy Rate (%)")

        if view_mode == "combined":
            fig_combined = px.bar(
                df_6_3_long,
                x="Age group",
                y="Literacy Rate (%)",
                color="Status",
                barmode="group",
                title="Literacy by Age Group and Poverty Status (Combined View)",
            )
            fig_combined.update_layout(height=800)
            return fig_combined
        else:
            # Split into poor and non-poor subsets
            df_poor = df_6_3_long[df_6_3_long["Status"].str.lower().str.contains("poor") & ~df_6_3_long["Status"].str.lower().str.contains("non")]
            df_nonpoor = df_6_3_long[df_6_3_long["Status"].str.lower().str.contains("non")]

            fig_poor = px.bar(
                df_poor,
                x="Age group",
                y="Literacy Rate (%)",
                color="Status",
                barmode="group",
                title="Literacy by Age Group (Poor Households)"
            )
            fig_nonpoor = px.bar(
                df_nonpoor,
                x="Age group",
                y="Literacy Rate (%)",
                color="Status",
                barmode="group",
                title="Literacy by Age Group (Non-poor Households)"
            )

            from plotly.subplots import make_subplots

            fig_split = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=[
                "Poor Households", "Non-poor Households"
            ])
            for trace in fig_poor.data:
                fig_split.add_trace(trace, row=1, col=1)
            for trace in fig_nonpoor.data:
                fig_split.add_trace(trace, row=2, col=1)

            fig_split.update_layout(
                height=900,
                title_text="Literacy by Age Group and Poverty Status (Split View)",
                showlegend=True
            )
            return fig_split
    elif dataset == "table_13" and indicator:
        if indicator not in df_13.columns:
            return fig
        df_13_filtered = df_13.iloc[1:][["Province", indicator]].copy()
        df_13_filtered[indicator] = pd.to_numeric(df_13_filtered[indicator], errors="coerce")
        fig_13_map = px.choropleth_mapbox(
            df_13_filtered,
            geojson=geojson,
            locations="Province",
            featureidkey="properties.ADM1_EN",
            color=indicator,
            color_continuous_scale="YlOrBr",
            range_color=[df_13_filtered[indicator].min(), df_13_filtered[indicator].max()],
            mapbox_style="carto-positron",
            zoom=5.8,
            center={"lat": 28.3949, "lon": 84.1240},
            opacity=0.7,
            hover_name="Province"
        )
        return fig_13_map
    elif dataset == "table_14" and indicator:
        if indicator not in df_14.columns:
            return fig
        df_14_filtered = df_14[df_14["Province"] != "Nepal"][["Province", indicator]].copy()
        fig_14_map = px.choropleth_mapbox(
            df_14_filtered,
            geojson=geojson,
            locations="Province",
            featureidkey="properties.ADM1_EN",
            color=indicator,
            color_continuous_scale="YlOrBr",
            mapbox_style="carto-positron",
            zoom=5.8,
            center={"lat": 28.3949, "lon": 84.1240},
            opacity=0.7,
            hover_name="Province"
        )
        return fig_14_map
    elif dataset == "ner" and indicator:
        df_plot = ner_provinces[["Region", indicator]].copy()
        df_plot.rename(columns={"Region": "Province"}, inplace=True)
        df_plot[indicator] = pd.to_numeric(df_plot[indicator], errors="coerce")
        df_plot[indicator] = df_plot[indicator] * 100
        fig_ner = px.choropleth_mapbox(
            df_plot,
            geojson=geojson,
            locations="Province",
            featureidkey="properties.ADM1_EN",
            color=indicator,
            color_continuous_scale="YlGnBu",
            mapbox_style="carto-positron",
            zoom=5.8,
            center={"lat": 28.3949, "lon": 84.1240},
            opacity=0.7,
            hover_name="Province"
        )
        return fig_ner
    elif dataset == "ger" and indicator:
        df_plot = ger_provinces[["Region", indicator]].copy()
        df_plot.rename(columns={"Region": "Province"}, inplace=True)
        df_plot[indicator] = pd.to_numeric(df_plot[indicator], errors="coerce")
        df_plot[indicator] = df_plot[indicator] * 100
        fig_ger = px.choropleth_mapbox(
            df_plot,
            geojson=geojson,
            locations="Province",
            featureidkey="properties.ADM1_EN",
            color=indicator,
            color_continuous_scale="YlGnBu",
            mapbox_style="carto-positron",
            zoom=5.8,
            center={"lat": 28.3949, "lon": 84.1240},
            opacity=0.7,
            hover_name="Province"
        )
        return fig_ger
    elif dataset == "table_13_weighted":
        fig_weighted = px.choropleth_mapbox(
            df_13_weighted,
            geojson=geojson,
            locations="Province",
            featureidkey="properties.ADM1_EN",
            color="Normalized Illiteracy Rate (%)",
            color_continuous_scale="Reds",
            mapbox_style="carto-positron",
            zoom=5.8,
            center={"lat": 28.3949, "lon": 84.1240},
            opacity=0.75,
            hover_name="Province",
            hover_data={"Normalized Illiteracy Rate (%)": True}
        )
        fig_weighted.update_layout(
            title="Normalized Illiteracy Rate by Province (Age 5+)",
            height=700
        )
        return fig_weighted
    elif dataset == "table_13":
        # fallback if no indicator
        return px.choropleth_mapbox(
            pd.DataFrame({"Province": [], "value": []}),
            geojson=geojson,
            locations="Province",
            featureidkey="properties.ADM1_EN",
            color="value",
            mapbox_style="carto-positron",
            zoom=5.5,
            center={"lat": 28.3949, "lon": 84.1240},
        )
    elif dataset == "table_14":
        return px.choropleth_mapbox(
            pd.DataFrame({"Province": [], "value": []}),
            geojson=geojson,
            locations="Province",
            featureidkey="properties.ADM1_EN",
            color="value",
            mapbox_style="carto-positron",
            zoom=5.5,
            center={"lat": 28.3949, "lon": 84.1240},
        )
    elif dataset == "oos":
        df_oos_nepal_plot = df_oos_nepal.copy()
        if "value" not in df_oos_nepal_plot.columns and "Rate" in df_oos_nepal_plot.columns:
            df_oos_nepal_plot.rename(columns={"Rate": "value"}, inplace=True)
        df_oos_nepal_plot["value"] = pd.to_numeric(df_oos_nepal_plot["value"], errors="coerce") * 100

        if indicator and indicator.startswith("OOS."):
            level_map = {"OOS.1": "Primary", "OOS.2": "Lower Secondary", "OOS.3": "Upper Secondary"}
            selected_level = level_map.get(indicator, "")
            df_oos_level = df_oos_nepal_plot[df_oos_nepal_plot["Level"] == selected_level].copy()
            fig = px.line(
                df_oos_level,
                x="Year",
                y="value",
                color="Gender",
                markers=True,
                title=f"Out-of-School Rates in Nepal ({selected_level})",
                labels={"value": "Percentage (%)"}
            )
            fig.update_layout(height=600)
            fig.update_xaxes(dtick=1, tickformat="d", tickmode="linear")
            return fig

        elif indicator == "all":
            fig = px.line(
                df_oos_nepal_plot,
                x="Year",
                y="value",
                color="Level",
                line_dash="Gender",
                markers=True,
                title="Out-of-School Rates in Nepal by Gender and Level (All Levels Combined)",
                labels={"value": "Percentage (%)"}
            )
            fig.update_layout(height=800)
            fig.update_xaxes(dtick=1, tickformat="d", tickmode="linear")
            return fig
    elif dataset == "ger_time" and indicator:
        # Combine GER, NER, and OOS data for the same level if indicator is GER or NER
        if indicator.startswith("NER.") or indicator.startswith("GER."):
            # Extract level number (e.g., "1", "2", "3")
            level = indicator.split(".")[1]
            ger_subset = df_ger_time[df_ger_time["indicator"] == f"GER.{level}"].copy()
            ner_subset = df_ner_time[df_ner_time["indicator"] == f"NER.{level}"].copy()

            ger_subset["Type"] = "GER"
            ner_subset["Type"] = "NER"

            df_combined = pd.concat([ger_subset, ner_subset], ignore_index=True)
            # Robust lowercase matching for OOS levels
            level_map = {"1": "Primary", "2": "Lower Secondary", "3": "Upper Secondary"}
            oos_level_name = level_map.get(level, "").lower()
            oos_subset = df_oos_nepal[df_oos_nepal["Level"].str.lower() == oos_level_name].copy()
            # Add conversion to percent for OOS data
            oos_subset["value"] = pd.to_numeric(oos_subset["value"], errors="coerce") * 100
            if not oos_subset.empty:
                oos_subset["Type"] = "OOS"
                oos_subset["indicator"] = f"OOS.{level}"
                oos_subset.rename(columns={"Rate": "value"}, inplace=True)
                df_combined = pd.concat([df_combined, oos_subset], ignore_index=True)
            df_combined["value"] = pd.to_numeric(df_combined["value"], errors="coerce")
            fig = px.line(
                df_combined,
                x="Year",
                y="value",
                color="Gender",
                line_dash="Type",
                markers=True,
                title=f"GER vs NER vs OOS Time Series: Level {level}",
                labels={"value": "Percentage (%)", "Type": "Indicator Type"}
            )
            fig.update_layout(height=600)
            fig.update_xaxes(dtick=1, tickformat="d", tickmode="linear")
            fig.update_layout(legend_title_text="Gender / Indicator Type")
            return fig
    else:
        empty_fig = px.choropleth_mapbox(
            pd.DataFrame({"Province": [], "value": []}),
            geojson=geojson,
            locations="Province",
            featureidkey="properties.ADM1_EN",
            color="value",
            mapbox_style="carto-positron",
            zoom=5.5,
            center={"lat": 28.3949, "lon": 84.1240},
        )
        return empty_fig


# Callback for sidebar chart (Table 13 & 14) and info
@app.callback(
    Output("sidebar-chart", "figure"),
    Output("province-data", "children"),
    Input("dataset-selector", "value"),
    Input("indicator-selector", "value"),
    Input("map", "clickData")
)
def update_sidebar_chart(dataset, indicator, clickData):
    import plotly.graph_objs as go
    # Determine source text to prepend
    source_text = None
    if dataset in ["table_6_1", "table_6_2", "table_6_3"]:
        source_text = html.P("Source: Nepal Living Standard IV 2022/2023", style={"fontSize": "12px", "fontStyle": "italic", "marginTop": "10px"})
    elif dataset in ["table_13", "table_14", "table_13_weighted"]:
        source_text = html.P("Source: Nepal Population and Housing Census 2021", style={"fontSize": "12px", "fontStyle": "italic", "marginTop": "10px"})
    elif dataset in ["ner", "ger"]:
        source_text = html.P("Source: UNESCO OPRI Database", style={"fontSize": "12px", "fontStyle": "italic", "marginTop": "10px"})
    elif dataset == "ger_time":
        source_text = html.Div([
            html.P("GER and NER Source: UNESCO OPRI Database", style={"fontSize": "12px", "fontStyle": "italic", "marginTop": "4px"}),
            html.P("OOS Source: UNESCO Institute for Statistics Database (UIS)", style={"fontSize": "12px", "fontStyle": "italic", "marginTop": "10px"})
        ])

    if dataset == "table_13_weighted":
        if clickData and "points" in clickData:
            province = clickData["points"][0].get("location")
            row = df_13_weighted[df_13_weighted["Province"] == province]
            if not row.empty:
                value = row.iloc[0]["Normalized Illiteracy Rate (%)"]
                content = html.Div([
                    source_text,
                    html.H4(f"{province}"),
                    html.P(f"Normalized Illiteracy Rate: {value:.2f}%"),
                    html.P("This value represents the percentage of the provincial population (aged 5 and above) who cannot read or write. It is calculated by dividing the illiterate population by the total population in that age group, providing a clearer picture of educational challenges normalized for population size.")
                ])
                return go.Figure(layout={"xaxis": {"visible": False}, "yaxis": {"visible": False}}), content
        return go.Figure(layout={"xaxis": {"visible": False}, "yaxis": {"visible": False}}), html.Div([
            source_text,
            html.P("Click on a province to see its normalized illiteracy rate.")
        ])
    elif dataset == "table_14" and indicator and indicator in df_14.columns:
        df_14_clean = df_14[df_14["Province"] != "Nepal"]
        fig = px.bar(
            df_14_clean,
            x="Province",
            y=indicator,
            title=f"Table 14: {indicator} by Province"
        )
        fig.update_layout(height=350)
        return fig, [source_text]
    elif dataset == "ner" and indicator:
        # Placeholder: show all provinces for indicator as bar (expand in next patch for other categories)
        df_plot = ner_provinces[["Region", indicator]].copy()
        df_plot[indicator] = pd.to_numeric(df_plot[indicator], errors="coerce")
        fig = px.bar(
            df_plot,
            x="Region",
            y=indicator,
            title=f"NER: {indicator} by Province"
        )
        fig.update_layout(height=350)
        return fig, html.Div([
            html.P("Source: Nepal Living Standards Survey IV 2023", style={"fontSize": "12px", "fontStyle": "italic", "marginTop": "10px"})
        ])
    elif dataset == "ger" and indicator:
        # Placeholder: show all provinces for indicator as bar (expand in next patch for other categories)
        df_plot = ger_provinces[["Region", indicator]].copy()
        df_plot[indicator] = pd.to_numeric(df_plot[indicator], errors="coerce")
        fig = px.bar(
            df_plot,
            x="Region",
            y=indicator,
            title=f"GER: {indicator} by Province"
        )
        fig.update_layout(height=350)
        return fig, html.Div([
            html.P("Source: Nepal Living Standards Survey IV 2023", style={"fontSize": "12px", "fontStyle": "italic", "marginTop": "10px"})
        ])
    elif dataset == "table_6_2":
        return dash.no_update, html.Div([
            html.P("Source: Nepal Living Standard IV 2022/2023", style={"fontSize": "12px", "fontStyle": "italic", "marginTop": "10px"})
        ])
    elif dataset == "table_6_3":
        return dash.no_update, html.Div([
            html.P("Source: Nepal Living Standard IV 2022/2023", style={"fontSize": "12px", "fontStyle": "italic", "marginTop": "10px"})
        ])
    elif dataset == "oos":
        return dash.no_update, html.Div([
            html.P("OOS Source: UNESCO Institute for Statistics Database (UIS)", style={"fontSize": "12px", "fontStyle": "italic", "marginTop": "10px"})
        ])
    elif dataset == "ger_time" and indicator:
        return go.Figure(), html.Div([
            html.P("GER and NER Source: UNESCO OPRI Database", style={"fontSize": "12px", "fontStyle": "italic", "marginTop": "10px"}),
            html.P("OOS Source: UNESCO Institute for Statistics Database (UIS)", style={"fontSize": "12px", "fontStyle": "italic", "marginTop": "10px"})
        ])
    elif dataset == "table_13" and indicator and indicator in df_13.columns:
        df_13_filtered = df_13.iloc[1:].copy()
        df_13_filtered[indicator] = pd.to_numeric(df_13_filtered[indicator], errors="coerce")
        fig = px.bar(
            df_13_filtered,
            x="Province",
            y=indicator,
            title=f"Table 13: {indicator} by Province"
        )
        fig.update_layout(height=350)
        return fig, [source_text]
    if dataset == "table_6_1":
        if clickData and "points" in clickData:
            province = clickData["points"][0].get("location")
            row = df_clean[df_clean["Province"] == province]
            if not row.empty:
                row = row.copy()
                row[["Male", "Female", "Total"]] = row[["Male", "Female", "Total"]].apply(pd.to_numeric, errors="coerce")
                values = row.iloc[0]
                fig = px.bar(
                    row,
                    x="Province",
                    y=["Male", "Female", "Total"],
                    barmode="group",
                    title=f"Literacy Rates for {province}",
                    labels={"value": "Literacy Rate (%)", "variable": "Gender"},
                )
                fig.update_layout(height=350)
                content = html.Div([
                    source_text,
                    html.H4(f"{province}"),
                    html.P(f"Male Literacy Rate: {values['Male']}%"),
                    html.P(f"Female Literacy Rate: {values['Female']}%"),
                    html.P(f"Total Literacy Rate: {values['Total']}%"),
                ])
                return fig, content

        # Default view: all provinces
        fig = px.bar(
            df_clean,
            x="Province",
            y="Total",
            title="Overall Literacy Rate by Province",
            labels={"Total": "Literacy Rate (%)"},
        )
        fig.update_layout(height=350)
        return fig, [source_text, html.P("Click on a province to see details.")]

    # (Removed duplicate 'elif dataset == "table_13_weighted"' block)
    # Return empty figure and None for other datasets or no clickData
    return go.Figure(), None

import os

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
