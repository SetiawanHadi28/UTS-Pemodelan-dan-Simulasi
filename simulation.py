import numpy as np
import streamlit as st
import altair as alt

from inventory_model import simulate_inventory, summarize, scenario_curves


st.set_page_config(
    page_title="Simulasi Sistem Dinamik Inventori Minimarket",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def _cached_simulation(params: tuple):
    (
        days,
        initial_stock,
        reorder_point,
        reorder_qty,
        mean_demand,
        demand_std,
        lead_time,
        seed,
    ) = params
    df = simulate_inventory(
        days=days,
        initial_stock=initial_stock,
        reorder_point=reorder_point,
        reorder_qty=reorder_qty,
        mean_demand=mean_demand,
        demand_std=demand_std,
        lead_time=lead_time,
        seed=seed,
    )
    summary = summarize(df)
    return df, summary


def render_summary_card(title: str, value):
    st.markdown(
        f"""
        <div style="padding:1rem;border-radius:12px;background-color:#f7f9ff;border:1px solid #e0e7ff;margin-bottom:0.5rem;">
            <p style="margin:0;color:#6c6f80;font-size:0.85rem;">{title}</p>
            <h3 style="margin:0;color:#1d2a6b;">{value}</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.title("Simulasi Sistem Dinamik Stok Barang Minimarket")
st.caption(
    "Model diskrit sederhana untuk memperkirakan kebutuhan restock, stockout, "
    "dan backlog berdasarkan parameter kebijakan inventori."
)

tab_sim, tab_scenario = st.tabs(["Simulasi Interaktif", "Contoh Grafik UTS"])

with tab_sim:
    col_form, col_summary = st.columns([3, 2])
    with col_form:
        st.subheader("Rencanakan Parameter Simulasi")
        with st.form("sim_form"):
            c1, c2 = st.columns(2)
            with c1:
                days = st.number_input("Durasi simulasi (hari)", 30, 365, 180, step=5)
                initial_stock = st.number_input("Stok awal", 0, 5000, 800, step=50)
                mean_demand = st.number_input("Permintaan rata-rata / hari", 1, 500, 120, step=5)
                lead_time = st.number_input("Lead time (hari)", 1, 30, 7)
            with c2:
                reorder_point = st.number_input("Reorder point", 0, 5000, 300, step=25)
                reorder_qty = st.number_input("Jumlah restock (lot)", 1, 5000, 600, step=25)
                demand_std = st.number_input("Standar deviasi permintaan", 0.0, 200.0, 30.0, step=5.0)
                seed = st.number_input("Seed acak", 0, 9999, 42)

            submitted = st.form_submit_button("Lihat Hasil Simulasi", use_container_width=True)

    if submitted:
        df, summary = _cached_simulation(
            (
                days,
                initial_stock,
                reorder_point,
                reorder_qty,
                mean_demand,
                demand_std,
                lead_time,
                seed,
            )
        )

        with col_summary:
            st.subheader("Ringkasan Utama")
            for key, value in summary.items():
                render_summary_card(key, f"{value:,.2f}" if isinstance(value, float) else value)

        st.divider()
        st.subheader("Detail Tren Inventori")
        sample_idx = np.linspace(0, len(df) - 1, num=min(20, len(df)), dtype=int)
        st.dataframe(
            df.iloc[sample_idx].reset_index(drop=True),
            use_container_width=True,
            height=480,
        )

        st.subheader("Grafik")
        line_df = df.melt(id_vars="Hari", value_vars=["Stok tersedia", "Backlog"])
        chart = (
            alt.Chart(line_df)
            .mark_line()
            .encode(
                x="Hari",
                y=alt.Y("value", title="Jumlah unit"),
                color=alt.Color("variable", title="Variabel"),
            )
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)

    else:
        with col_summary:
            st.info("Isi formulir dan klik **Lihat Hasil Simulasi** untuk melihat ringkasan.")

with tab_scenario:
    st.subheader("Skenario Referensi UTS")
    st.write("Grafik ini membantu membandingkan pola restock atau permintaan pada beberapa strategi.")
    scenario_df = scenario_curves()
    chart = (
        alt.Chart(scenario_df.melt("Hari"))
        .mark_line()
        .encode(
            x="Hari",
            y=alt.Y("value", title="Unit"),
            color=alt.Color("variable", title="Skenario"),
        )
        .properties(height=320, title="Perbandingan stok / subscriber (analog)")
    )
    st.altair_chart(chart, use_container_width=True)

    st.write("Contoh estimasi permintaan harian untuk ketiga skenario.")
    demand_chart = (
        alt.Chart(scenario_df.assign(Demand=1000))
        .mark_line(color="#2563eb")
        .encode(x="Hari", y=alt.Y("Demand", title="Permintaan"))
        .properties(height=300, title="Daily demand (model)")
    )
    st.altair_chart(demand_chart, use_container_width=True)

st.caption(
    "Gunakan hasil simulasi sebagai referensi awal. Sesuaikan parameter untuk menguji kebijakan restock lainnya."
)

