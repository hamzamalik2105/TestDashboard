import streamlit as st
import pandas as pd
import math
import requests
from bs4 import BeautifulSoup
import plotly.express as px

# Configure page
st.set_page_config(
    page_title="Media Performance Dashboard",
    layout="wide"
)

# Custom CSS for layout and containers
st.markdown("""
<style>
.block-container { padding: 1rem 1rem; }
.card-container {
    padding: 8px;
    margin-bottom: 12px;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    background-color: white;
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.asset-title {
    font-size: 0.82rem;
    margin: 0;
    font-weight: 600;
    min-height: 1.70em;
    max-height: 1.7em;
    overflow-y: auto;
}
.card-container p {
    margin: 2px 0;
    font-size: 0.9rem;
}
.bold-title { font-weight: 600; }
.metric-item { font-size: 13px; line-height: 1.4; margin-right: 12px; }
.right-align { display: flex; justify-content: space-between; align-items: center; }
</style>
""", unsafe_allow_html=True)

# Load and clean data
def load_data():
    df = pd.read_excel("videos.xlsx")
    for col in ['Clicks','CTR','Impr.','Cost','Installs','Installs per (1000) impressions']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df.dropna(subset=['Clicks','CTR','Impr.','Cost','Installs'], inplace=True)
    if 'Cost' in df.columns and 'Installs' in df.columns:
        df['CPI'] = df['Cost'] / df['Installs'].replace(0,1)
    return df

@st.cache_data
def get_youtube_title(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        title_tag = BeautifulSoup(res.text, 'html.parser').find('title')
        return title_tag.text.replace(' - YouTube','').strip() if title_tag else url.split('/')[-1]
    except:
        return url.split('/')[-1]

@st.cache_data
def is_image_url(url):
    try:
        res = requests.head(url, allow_redirects=True, timeout=5)
        return 'image' in res.headers.get('Content-Type','')
    except:
        return False

# Main loading
with st.spinner('Loading media data...'):
    df = load_data()

# Sidebar filters
st.sidebar.title('Filter Media')
asset_types = df['Asset type'].unique()
selected_assets = st.sidebar.multiselect('Asset Type', asset_types, default=asset_types)
performance_opts = df['Performance'].unique()
selected_perf = st.sidebar.multiselect('Performance', performance_opts, default=performance_opts)
sort_by = st.sidebar.selectbox('Sort By', ['None','Clicks','Impr.','CTR','Cost','Installs','CPI'])
order = st.sidebar.radio('Order', ['High to Low','Low to High'])

# Filter & sort
df_filtered = df[df['Asset type'].isin(selected_assets) & df['Performance'].isin(selected_perf)].copy()
if sort_by != 'None':
    df_filtered = df_filtered.sort_values(by=sort_by, ascending=(order=='Low to High'))
if df_filtered.empty:
    st.warning('No data matches filters.')
    st.stop()

# Header & summary
st.markdown(f"<div class='right-align'><h6>Media Dashboard</h6><p>Showing {len(df_filtered)} items</p></div>", unsafe_allow_html=True)
with st.expander('Performance Summary', expanded=True):
    avg = lambda c: df[c].mean()
    # Four columns for metrics and one wide for chart
    col1, col2, col3, col4 = st.columns([1,1,1,2])
    with col1:
        st.metric('Avg Clicks', f"{avg('Clicks'):,.1f}")
        st.metric('Avg Impr.', f"{avg('Impr.'):,.1f}")
    with col2:
        st.metric('Avg Installs', f"{avg('Installs'):,.1f}")
        st.metric('Avg Cost', f"{avg('Cost'):,.2f}")
    with col3:
        st.metric('Avg CTR', f"{avg('CTR'):.2%}")
        st.metric('Avg CPI', f"{avg('CPI'):,.2f}")
    with col4:
        # Asset distribution bar
        dist = df['Asset type'].value_counts().reset_index()
        dist.columns = ['Asset','Count']
        fig = px.bar(
            dist,
            x='Asset',
            y='Count',
            color='Asset',
            height=170,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_layout(
            title_text="Asset Distribution",
            title_x=0.02,
            title_xanchor='left',
            showlegend=False,
            xaxis_title=None,
            margin=dict(t=30, b=20, l=10, r=10)
        )
        st.plotly_chart(fig, use_container_width=True)

# Pagination setup
per_page = 10
total = len(df_filtered)
pages = math.ceil(total/per_page)
page = st.number_input('Page',1,pages,1) if pages>1 else 1
start = (page-1)*per_page
subset = df_filtered.iloc[start:start+per_page]

# Render cards with standardized order and sizing
for row_start in range(0, len(subset), 5):
    chunk = subset.iloc[row_start:row_start+5]
    cols = st.columns(5)
    for idx, (_, row) in enumerate(chunk.iterrows()):
        with cols[idx]:
            url = str(row['Asset'])
            is_yt = url.startswith('http') and ('youtube.com' in url or 'youtu.be' in url)
            is_img = url.startswith('http') and not is_yt and is_image_url(url)
            # Determine display title
            if is_yt:
                display_title = get_youtube_title(url)
            elif is_img:
                display_title = ''
            else:
                display_title = row['Asset']
            elements = []
            elements.append(f"<h5 class='asset-title'>{display_title}</h5>")
            elements.append(f"<p><span class='bold-title'>Type:</span> {row['Asset type']}</p>")
            elements.append(f"<p><span class='bold-title'>Performance:</span> {row['Performance']}</p>")
            # Media
            if is_yt:
                embed = url.replace('watch?v=','embed/').replace('youtu.be/','youtube.com/embed/')
                elements.append(f"<iframe src='{embed}' width='100%' height='150' frameborder='0' allowfullscreen></iframe>")
            elif is_img:
                elements.append(f"<img src='{url}' style='width:100%; height:150px; object-fit:cover;'/>" )
            # Metrics
            left = (f"<div>Impr.<br><b>{row['Impr.']:,}</b><br>Clicks<br><b>{row['Clicks']:,}</b><br>Installs<br><b>{row['Installs']:,}</b></div>")
            right = (f"<div>CTR<br><b>{row['CTR']:.2%}</b><br>Cost<br><b>{row['Cost']:,.2f}</b><br>CPI<br><b>{row['CPI']:,.2f}</b></div>")
            elements.append(f"<div style='display:flex; gap:12px; margin-top:4px;'>{left}{right}</div>")
            # Render
            html = "<div class='card-container'>" + "".join(elements) + "</div>"
            st.markdown(html, unsafe_allow_html=True)

# Footer
if pages>1:
    st.caption(f"Showing {start+1}-{min(start+per_page,total)} of {total}")
