import streamlit as st
import pandas as pd
import numpy as np
import re
import json
import plotly.express as px
from sqlalchemy import create_engine
from urllib.parse import quote_plus
from datetime import datetime
import google.generativeai as genai

# Configuração da tela
st.set_page_config(page_title="Painel Comercial - Star Flash IA", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f1f5f9; }
    h1, h2, h3, h4 { color: #0f172a; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# Configuração da IA (Gemini)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    ia_configurada = True
except Exception:
    ia_configurada = False

@st.cache_resource
def get_engine():
    usuario_mysql = "65895484000120_ro"
    senha_mysql = quote_plus(st.secrets["DB_SENHA"])
    host_mysql = "e2dw.aokiinova.com.br"
    banco_mysql = "65895484000120"
    uri = f"mysql+pymysql://{usuario_mysql}:{senha_mysql}@{host_mysql}:3306/{banco_mysql}"
    return create_engine(uri)

engine = get_engine()

# --- SISTEMA DE LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.perfil = None
    st.session_state.vendedor_nome = None

if not st.session_state.autenticado:
    st.title("🔒 Acesso Restrito - Star Flash (Cérebro Gemini)")
    st.markdown("Entre com suas credenciais para acessar o ambiente com Inteligência Artificial real.")
    
    with st.form("form_login"):
        usuario_input = st.text_input("Usuário (Nome do Vendedor ou MASTER):").strip()
        senha_input = st.text_input("Senha:", type="password")
        btn_login = st.form_submit_button("Entrar no Sistema", type="primary")
        
        if btn_login:
            if usuario_input.upper() == "MASTER" and senha_input == "STAR@2026":
                st.session_state.autenticado = True
                st.session_state.perfil = "MASTER"
                st.session_state.vendedor_nome = "TODOS"
                st.rerun()
            elif usuario_input != "" and senha_input == "vendas123":
                st.session_state.autenticado = True
                st.session_state.perfil = "VENDEDOR"
                st.session_state.vendedor_nome = usuario_input.upper()
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos.")
    st.stop()

# --- BARRA LATERAL ---
st.sidebar.title("👤 Sessão Ativa (Sandbox IA)")
st.sidebar.write(f"**Perfil:** {st.session_state.perfil}")
st.sidebar.write(f"**Usuário:** {st.session_state.vendedor_nome}")

if st.sidebar.button("🚪 Sair / Trocar Usuário"):
    st.session_state.autenticado = False
    st.session_state.perfil = None
    st.session_state.vendedor_nome = None
    st.rerun()

st.title("📊 Painel de Desempenho Comercial - Star Flash (Com Gemini IA)")

# ==========================================
# ESTRUTURA DE ABAS
# ==========================================
aba1, aba2, aba3, aba4 = st.tabs([
    "📊 Visão Geral da Carteira", 
    "🔎 Raio-X do Cliente", 
    "🏆 Performance do Vendedor",
    "🧠 Chatbot IA (Analítico)"
])

# ==========================================
# ABA 1: VISÃO GERAL
# ==========================================
with aba1:
    st.markdown("### Filtros da Visão Geral")
    col_f1, col_f2, col_f3 = st.columns(3)
    
    if st.session_state.perfil == "MASTER":
        filtro_vendedor_master = col_f1.text_input("Vendedor (Deixe vazio para TODOS):", "", key="vendedor_aba1").strip()
    else:
        col_f1.info(f"🔒 Carteira: **{st.session_state.vendedor_nome}**")
        filtro_vendedor_master = ""

    filial_input = col_f2.text_input("Filial (Ex: 0001 ou vazio):", "").strip()
    busca_cliente = col_f3.text_input("Nome do Cliente (Opcional):", "").strip()
    
    col_f4, col_f5, col_f6 = st.columns(3)
    tipo_data = col_f4.selectbox("Filtrar por qual Data?", ["Data de Emissão (Pedido)", "Data de Faturamento"])
    usar_filtro_data = col_f5.checkbox("Ativar Filtro por Data", value=False)
    
    if usar_filtro_data:
        data_inicio = col_f5.date_input("Data Inicial", datetime.now().date())
        data_fim = col_f6.date_input("Data Final", datetime.now().date())
    
    status_opcoes = ["TODOS", "Aberto", "Fat_OK", "Cancelado"]
    status_filtro = st.selectbox("Status:", status_opcoes)
    limite_registros = st.slider("Limite de linhas:", 100, 3000, 1000, step=100)

    if st.button("🚀 Executar Consulta (Visão Geral)", type="primary"):
        with st.spinner("Buscando dados no E2DW..."):
            try:
                query = """
                    SELECT 
                        PedVenda AS 'Nº Pedido', Data_Ped AS 'Emissão', Data_Fech AS 'Fechamento', 
                        Status AS 'Status', CodCliente AS 'Cód. Cliente', Nome_Clien AS 'Cliente', 
                        Filial AS 'Filial', i_codProd AS 'Cód. Produto', i_NomeProd AS 'Descrição o Item', 
                        i_Qtdade AS 'Qtd', i_Unid AS 'Unidade', i_Preco AS 'Preço Unit.', i_Vtotal AS 'Total Item', 
                        Dt_Entrega AS 'Data Entrega', Dt_Fatura AS 'Data Faturamento', 
                        i_notas AS 'Nota Fiscal', Vendedor AS 'Vendedor', Cidade AS 'Cidade', UF AS 'UF' 
                    FROM PEDIDODEVENDA WHERE 1=1
                """
                params = {}
                
                if st.session_state.perfil == "VENDEDOR":
                    query += " AND Vendedor LIKE %(vendedor_logado)s"
                    params["vendedor_logado"] = f"%{st.session_state.vendedor_nome}%"
                elif st.session_state.perfil == "MASTER" and filtro_vendedor_master:
                    query += " AND Vendedor LIKE %(vendedor_master)s"
                    params["vendedor_master"] = f"%{filtro_vendedor_master}%"

                if filial_input:
                    query += " AND Filial = %(filial)s"
                    params["filial"] = filial_input

                if busca_cliente:
                    query += " AND Nome_Clien LIKE %(cliente)s"
                    params["cliente"] = f"%{busca_cliente}%"
                    
                if status_filtro != "TODOS":
                    query += " AND Status = %(status)s"
                    params["status"] = status_filtro

                if usar_filtro_data:
                    coluna_alvo = "Data_Ped" if tipo_data == "Data de Emissão (Pedido)" else "Dt_Fatura"
                    query += f" AND {coluna_alvo} BETWEEN %(dt_ini)s AND %(dt_fim)s"
                    params["dt_ini"] = data_inicio.strftime('%Y%m%d')
                    params["dt_fim"] = data_fim.strftime('%Y%m%d')
                    
                query += f" ORDER BY Data_Ped DESC, PedVenda DESC LIMIT {limite_registros};"
                df = pd.read_sql(query, engine, params=params)
                
                if df.empty:
                    st.warning("⚠️ Nenhum registro encontrado.")
                else:
                    for col in ['Emissão', 'Fechamento', 'Data Entrega', 'Data Faturamento']:
                        if col in df.columns:
                            df[col] = pd.to_datetime(df[col], format='%Y%m%d', errors='coerce').dt.strftime('%d/%m/%Y').fillna('')

                    df['Nº Pedido'] = df['Nº Pedido'].astype(str)
                    st.session_state.df_resultado = df
                    st.success("✅ Consulta realizada!")
            except Exception as e:
                st.error(f"❌ Erro: {e}")

    if "df_resultado" in st.session_state and not st.session_state.df_resultado.empty:
        df = st.session_state.df_resultado
        
        col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
        df_abertos = df[df['Status'] == 'Aberto']
        col_kpi1.metric("Pedidos Abertos", f"{df_abertos['Nº Pedido'].nunique():,} ped.", f"R$ {df_abertos['Total Item'].sum():,.2f}")
        df_faturados = df[df['Status'] == 'Fat_OK']
        col_kpi2.metric("Pedidos Faturados", f"{df_faturados['Nº Pedido'].nunique():,} ped.", f"R$ {df_faturados['Total Item'].sum():,.2f}")
        col_kpi3.metric("Valor Total Geral", f"{df['Nº Pedido'].nunique():,} pedidos únicos", f"R$ {df['Total Item'].sum():,.2f}")
        st.markdown("---")

        st.subheader("📋 Resumo de Pedidos")
        df_resumo = df.groupby(['Nº Pedido', 'Emissão', 'Status', 'Cliente', 'Filial', 'Vendedor'], as_index=False)['Total Item'].sum()
        st.dataframe(df_resumo, use_container_width=True, hide_index=True)
        st.markdown("---")

        st.subheader("🔍 Detalhamento de Itens")
        df['Pedido_Cliente'] = df['Nº Pedido'] + " - " + df['Cliente'].astype(str)
        escolha = st.selectbox("Selecione o Pedido (Nº e Cliente):", df[['Nº Pedido', 'Pedido_Cliente']].drop_duplicates().sort_values(by='Nº Pedido', ascending=False)['Pedido_Cliente'].tolist())
        
        if escolha:
            pedido_sel = escolha.split(" - ")[0]
            st.dataframe(df[df['Nº Pedido'] == pedido_sel][['Cód. Produto', 'Descrição o Item', 'Qtd', 'Unidade', 'Preço Unit.', 'Total Item', 'Data Entrega', 'Nota Fiscal']], use_container_width=True, hide_index=True)

# ==========================================
# ABA 2: RAIO-X DO CLIENTE 
# ==========================================
with aba2:
    st.markdown("### 🔎 Dossiê e Saúde do Cliente")
    
    col_busca1, col_busca2 = st.columns([3, 1])
    termo_busca_rx = col_busca1.text_input("Digite parte do nome (ex: Pirelli, Dana):", key="input_termo_rx").strip()
    
    if col_busca2.button("🔍 Buscar Clientes na Base", use_container_width=True, key="btn_rx"):
        if not termo_busca_rx:
            st.warning("⚠️ Digite um termo para buscar as opções disponíveis.")
        else:
            with st.spinner("Procurando clientes compatíveis..."):
                try:
                    query_busca = "SELECT DISTINCT Nome_Clien, Cidade, UF FROM PEDIDODEVENDA WHERE Status = 'Fat_OK' AND Nome_Clien LIKE %(termo)s"
                    params_busca = {"termo": f"%{termo_busca_rx}%"}
                    if st.session_state.perfil == "VENDEDOR":
                        query_busca += " AND Vendedor LIKE %(vendedor_logado)s"
                        params_busca["vendedor_logado"] = f"%{st.session_state.vendedor_nome}%"

                    df_opcoes = pd.read_sql(query_busca, engine, params=params_busca)
                    
                    if df_opcoes.empty:
                        st.warning(f"Nenhum cliente faturado encontrado com '{termo_busca_rx}'.")
                        if "clientes_busca_rx" in st.session_state: del st.session_state["clientes_busca_rx"]
                    else:
                        st.session_state.clientes_busca_rx = df_opcoes
                        st.success(f"✅ Encontramos {len(df_opcoes)} opção(ões)!")
                except Exception as e:
                    st.error(f"❌ Erro na busca: {e}")

    st.markdown("---")

    if "clientes_busca_rx" in st.session_state and not st.session_state.clientes_busca_rx.empty:
        df_clientes = st.session_state.clientes_busca_rx
        df_clientes['Opcao_Formatada'] = df_clientes['Nome_Clien'] + " | " + df_clientes['Cidade'] + " - " + df_clientes['UF']
        cliente_escolhido = st.selectbox("Selecione o Cliente Exato para o Dossiê:", df_clientes['Opcao_Formatada'].tolist())
        
        if st.button("📊 Gerar Raio-X Completo", type="primary", key="btn_gerar_rx"):
            nome_exato = cliente_escolhido.split(" | ")[0]
            cidade_exata = cliente_escolhido.split(" | ")[1].split(" - ")[0]
            
            with st.spinner(f"Gerando análise para {nome_exato}..."):
                try:
                    hoje = pd.to_datetime('today')
                    data_6_meses_str = (hoje - pd.DateOffset(months=6)).strftime('%Y%m%d')

                    query_rx = """
                        SELECT PedVenda, Filial, i_codProd, i_NomeProd, i_Preco, i_Qtdade, i_Unid, i_Vtotal, Data_Ped, Dt_Fatura 
                        FROM PEDIDODEVENDA 
                        WHERE Status = 'Fat_OK' AND Nome_Clien = %(nome_c)s AND Cidade = %(cidade_c)s
                    """
                    
                    query_pedidos_recentes = """
                        SELECT Filial, Status, PedVenda, Data_Ped, Dt_Fatura, condPagto, 
                               FRETE, TRANSPORTA, REDESPACHO, i_notas, i_Vtotal, 
                               i_codProd, i_NomeProd, i_Qtdade, i_Unid, i_Preco
                        FROM PEDIDODEVENDA 
                        WHERE Nome_Clien = %(nome_c)s AND Cidade = %(cidade_c)s 
                          AND Data_Ped >= %(data_6m)s
                    """

                    query_abc = "SELECT Nome_Clien, SUM(i_Vtotal) as Total FROM PEDIDODEVENDA WHERE Status = 'Fat_OK'"
                    
                    params_rx = {"nome_c": nome_exato, "cidade_c": cidade_exata, "data_6m": data_6_meses_str}

                    if st.session_state.perfil == "VENDEDOR":
                        query_rx += " AND Vendedor LIKE %(vendedor_logado)s"
                        query_pedidos_recentes += " AND Vendedor LIKE %(vendedor_logado)s"
                        query_abc += " AND Vendedor LIKE %(vendedor_logado)s"
                        params_rx["vendedor_logado"] = f"%{st.session_state.vendedor_nome}%"
                    
                    query_abc += " GROUP BY Nome_Clien ORDER BY Total DESC"

                    df_rx = pd.read_sql(query_rx, engine, params=params_rx)
                    df_recentes = pd.read_sql(query_pedidos_recentes, engine, params=params_rx)
                    df_abc_base = pd.read_sql(query_abc, engine, params=params_rx if st.session_state.perfil == "VENDEDOR" else {})

                    if df_rx.empty:
                        st.warning("Dados de faturamento não localizados para esta combinação.")
                    else:
                        df_rx['Data_Fatura_Real'] = pd.to_datetime(df_rx['Dt_Fatura'], format='%Y%m%d', errors='coerce')
                        df_rx['Data_Emissao_Real'] = pd.to_datetime(df_rx['Data_Ped'], format='%Y%m%d', errors='coerce')
                        df_rx['Mes_Ano'] = df_rx['Data_Fatura_Real'].dt.strftime('%Y-%m')

                        # --- CLASSIFICAÇÃO ABC ---
                        df_abc_base['Perc'] = df_abc_base['Total'] / df_abc_base['Total'].sum()
                        df_abc_base['Perc_Acumulado'] = df_abc_base['Perc'].cumsum()
                        df_abc_base['Classe'] = np.where(df_abc_base['Perc_Acumulado'] <= 0.8, 'A', np.where(df_abc_base['Perc_Acumulado'] <= 0.95, 'B', 'C'))
                        classe_cliente = df_abc_base[df_abc_base['Nome_Clien'] == nome_exato]['Classe'].values
                        
                        str_classe = "Desconhecida"
                        if len(classe_cliente) > 0:
                            if classe_cliente[0] == 'A': str_classe = "🏆 CLIENTE CLASSE A (Foco Total)"
                            elif classe_cliente[0] == 'B': str_classe = "📈 CLIENTE CLASSE B (Intermediário)"
                            else: str_classe = "🌱 CLIENTE CLASSE C (Pequeno/Esporádico)"

                        st.markdown(f"### {nome_exato}")
                        st.info(f"**Classificação na sua Carteira:** {str_classe}")

                        # --- KPIS DE SAÚDE ---
                        ano_atual = hoje.year
                        faturamento_ytd = df_rx[df_rx['Data_Fatura_Real'].dt.year == ano_atual]['i_Vtotal'].sum()
                        ticket_medio = df_rx.groupby('PedVenda')['i_Vtotal'].sum().mean()
                        lead_time = (df_rx['Data_Fatura_Real'] - df_rx['Data_Emissao_Real']).dt.days.mean()
                        meses_distintos = df_rx['Data_Fatura_Real'].dt.to_period('M').nunique()
                        fat_medio_mensal = df_rx['i_Vtotal'].sum() / meses_distintos if meses_distintos > 0 else 0
                        
                        datas_compras = df_rx['Data_Fatura_Real'].dt.date.drop_duplicates().sort_values()
                        ciclo_medio = pd.Series(datas_compras).diff().dt.days.mean() if len(datas_compras) > 1 else 0
                        ultima_compra = pd.to_datetime(datas_compras.iloc[-1])
                        dias_sem_comprar = (hoje - ultima_compra).days

                        k1, k2, k3, k4 = st.columns(4)
                        k1.metric("Faturamento YTD", f"R$ {faturamento_ytd:,.2f}")
                        k2.metric("Fat. Médio Mensal", f"R$ {fat_medio_mensal:,.2f}")
                        k3.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")
                        k4.metric("Tempo Méd. Faturamento", f"{lead_time:.0f} dias" if pd.notnull(lead_time) else "N/A")

                        status_cor = "🟢 Normal"
                        if ciclo_medio > 0:
                            if dias_sem_comprar > (ciclo_medio * 1.5): status_cor = "🔴 ALERTA DE RISCO (Pulou Frequência)"
                            elif dias_sem_comprar > ciclo_medio: status_cor = "🟡 ATENÇÃO (Atraso no Ciclo)"
                        st.write(f"**Termômetro de Recorrência:** {status_cor} (Comprou há {dias_sem_comprar} dias. Ciclo Normal: {ciclo_medio:.0f} dias)")
                        st.markdown("---")

                        # --- GRÁFICOS FINANCEIROS ---
                        st.markdown("#### 📊 Evolução Financeira (Faturamento)")
                        col_g1, col_g2 = st.columns(2)
                        
                        df_fat_mensal = df_rx.groupby('Mes_Ano')['i_Vtotal'].sum().reset_index().sort_values('Mes_Ano')
                        fig1 = px.bar(df_fat_mensal, x='Mes_Ano', y='i_Vtotal', text_auto='.2s', title="Faturamento Total por Mês")
                        fig1.update_layout(xaxis_title="Mês", yaxis_title="Faturamento (R$)")
                        col_g1.plotly_chart(fig1, use_container_width=True)
                        
                        df_fat_prod = df_rx.groupby(['Mes_Ano', 'i_NomeProd'])['i_Vtotal'].sum().reset_index().sort_values('Mes_Ano')
                        fig2 = px.bar(df_fat_prod, x='Mes_Ano', y='i_Vtotal', color='i_NomeProd', title="Faturamento Mensal (Por Produto)")
                        fig2.update_layout(xaxis_title="Mês", yaxis_title="Faturamento (R$)", showlegend=False)
                        col_g2.plotly_chart(fig2, use_container_width=True)

                        st.markdown("---")

                        st.session_state.df_rx_volume = df_rx 
                        st.session_state.df_rx_recentes = df_recentes
                        st.success("Análise de Faturamento, Histórico e Tabela de Pedidos gerados com sucesso! Desça a tela para ver os detalhes.")
                        
                except Exception as e:
                    st.error(f"❌ Erro ao processar: {e}")

    # ==========================================
    # INTERAÇÕES PÓS-BOTÃO (GRÁFICOS E PEDIDOS)
    # ==========================================
    if "df_rx_volume" in st.session_state and "df_rx_recentes" in st.session_state:
        df_rx = st.session_state.df_rx_volume
        df_rec = st.session_state.df_rx_recentes
        
        st.markdown("#### 📦 Análise de Volume Físico (Qtd Vendida)")
        col_v1, col_v2 = st.columns(2)
        lista_produtos = df_rx['i_NomeProd'].unique()
        prod_escolhido = col_v1.selectbox("1. Selecione o Produto para analisar Volume:", lista_produtos, key="prod_vol")
        
        if prod_escolhido:
            df_prod = df_rx[df_rx['i_NomeProd'] == prod_escolhido]
            lista_unidades = df_prod['i_Unid'].unique()
            unid_escolhida = col_v2.selectbox("2. Selecione a Unidade de Medida (Filtro):", lista_unidades, key="unid_vol")
            
            if unid_escolhida:
                df_vol = df_prod[df_prod['i_Unid'] == unid_escolhida]
                df_vol_mensal = df_vol.groupby('Mes_Ano')['i_Qtdade'].sum().reset_index().sort_values('Mes_Ano')
                fig3 = px.bar(df_vol_mensal, x='Mes_Ano', y='i_Qtdade', text_auto=True, 
                            title=f"Volume Mensal de '{prod_escolhido}' (em {unid_escolhida})", color_discrete_sequence=['#10b981'])
                st.plotly_chart(fig3, use_container_width=True)

        st.markdown("---")
        
        st.markdown("#### 💲 Histórico Detalhado de Preços (12 Meses)")
        df_rx_12m = df_rx[df_rx['Data_Fatura_Real'] >= (pd.to_datetime('today') - pd.DateOffset(years=1))]
        if not df_rx_12m.empty:
            df_precos = df_rx_12m.groupby(['Filial', 'i_codProd', 'i_NomeProd', 'i_Unid']).agg(
                Menor_Preco=('i_Preco', 'min'), Preco_Medio=('i_Preco', 'mean'),
                Preco_Maximo=('i_Preco', 'max'), Qtd_Total=('i_Qtdade', 'sum'), Ultima_Data=('Data_Fatura_Real', 'max')
            ).reset_index()
            for c in ['Menor_Preco', 'Preco_Medio', 'Preco_Maximo']: df_precos[c] = df_precos[c].apply(lambda x: f"R$ {x:,.2f}")
            df_precos['Ultima_Data'] = df_precos['Ultima_Data'].dt.strftime('%d/%m/%Y')
            df_precos.rename(columns={'i_codProd': 'Cód.', 'i_NomeProd': 'Produto', 'i_Unid': 'UN', 'Menor_Preco': 'Menor R$', 'Preco_Medio': 'Médio R$', 'Preco_Maximo': 'Máximo R$', 'Qtd_Total': 'Vol. 12M', 'Ultima_Data': 'Última Compra'}, inplace=True)
            st.dataframe(df_precos, use_container_width=True, hide_index=True)

        st.markdown("---")

        st.markdown("#### 🛒 Rastreabilidade: Pedidos dos Últimos 6 Meses")
        if not df_rec.empty:
            df_rec['Emissão'] = pd.to_datetime(df_rec['Data_Ped'], format='%Y%m%d', errors='coerce').dt.strftime('%d/%m/%Y').fillna('')
            df_rec['Faturamento'] = pd.to_datetime(df_rec['Dt_Fatura'], format='%Y%m%d', errors='coerce').dt.strftime('%d/%m/%Y').fillna('')
            df_rec['PedVenda'] = df_rec['PedVenda'].astype(str)

            df_resumo_ped = df_rec.groupby(['Filial', 'Status', 'PedVenda', 'Emissão', 'Faturamento', 'condPagto', 'FRETE', 'TRANSPORTA', 'REDESPACHO', 'i_notas'], as_index=False)['i_Vtotal'].sum()
            df_resumo_ped.rename(columns={'PedVenda': 'Nº Pedido', 'condPagto': 'Pagamento', 'FRETE': 'Frete', 'TRANSPORTA': 'Transportadora', 'REDESPACHO': 'Redespacho', 'i_notas': 'Nota Fiscal', 'i_Vtotal': 'Valor Total'}, inplace=True)
            
            st.markdown("##### 🔍 Filtrar Histórico Recente")
            cf1, cf2, cf3 = st.columns(3)
            
            status_opcoes = ["TODOS"] + list(df_resumo_ped['Status'].unique())
            f_status = cf1.selectbox("Filtrar por Status do Pedido:", status_opcoes, key="f_status_rx")
            
            df_resumo_ped['Emissao_DT'] = pd.to_datetime(df_resumo_ped['Emissão'], format='%d/%m/%Y', errors='coerce')
            df_resumo_ped['Fatura_DT'] = pd.to_datetime(df_resumo_ped['Faturamento'], format='%d/%m/%Y', errors='coerce')

            usar_dt_emissao = cf2.checkbox("Ativar Filtro: Data de Emissão", key="chk_dt_emi")
            if usar_dt_emissao:
                dt_emi = cf2.date_input("Período de Emissão (Início e Fim):", [], key="dt_emi_val")
            
            usar_dt_fatura = cf3.checkbox("Ativar Filtro: Data de Faturamento", key="chk_dt_fat")
            if usar_dt_fatura:
                dt_fat = cf3.date_input("Período de Faturamento (Início e Fim):", [], key="dt_fat_val")

            df_filtrado = df_resumo_ped.copy()
            
            if f_status != "TODOS":
                df_filtrado = df_filtrado[df_filtrado['Status'] == f_status]
            if usar_dt_emissao and len(dt_emi) == 2:
                df_filtrado = df_filtrado[(df_filtrado['Emissao_DT'].dt.date >= dt_emi[0]) & (df_filtrado['Emissao_DT'].dt.date <= dt_emi[1])]
            if usar_dt_fatura and len(dt_fat) == 2:
                df_filtrado = df_filtrado[df_filtrado['Fatura_DT'].notna()]
                df_filtrado = df_filtrado[(df_filtrado['Fatura_DT'].dt.date >= dt_fat[0]) & (df_filtrado['Fatura_DT'].dt.date <= dt_fat[1])]

            df_exibicao = df_filtrado.drop(columns=['Emissao_DT', 'Fatura_DT']).copy()
            df_exibicao['Valor Total'] = df_exibicao['Valor Total'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

            st.markdown("##### 🔎 Detalhar Pedido")
            df_filtrado['Opcao_Pedido'] = df_filtrado['Nº Pedido'] + " - " + df_filtrado['Status'] + " - Emissão: " + df_filtrado['Emissão']
            lista_pedidos_recentes = df_filtrado.sort_values('Emissao_DT', ascending=False)['Opcao_Pedido'].tolist()
            
            pedido_sel_rx = st.selectbox("Selecione o Pedido para visualizar os itens:", [""] + lista_pedidos_recentes, key="sel_det_ped")
            
            if pedido_sel_rx:
                num_pedido_exato = pedido_sel_rx.split(" - ")[0]
                dados_ped = df_resumo_ped[df_resumo_ped['Nº Pedido'] == num_pedido_exato].iloc[0]
                itens_ped = df_rec[df_rec['PedVenda'] == num_pedido_exato]

                st.info(f"Visualizando Pedido: **{num_pedido_exato}**")
                cp1, cp2, cp3, cp4 = st.columns(4)
                cp1.metric("Nº Pedido", dados_ped['Nº Pedido'])
                cp2.metric("Nota Fiscal", dados_ped['Nota Fiscal'] if dados_ped['Nota Fiscal'] else "N/A")
                cp3.metric("Data Emissão", dados_ped['Emissão'])
                cp4.metric("Data Faturamento", dados_ped['Faturamento'] if dados_ped['Faturamento'] else "Pendente")
                
                itens_ped_show = itens_ped[['i_codProd', 'i_NomeProd', 'i_Qtdade', 'i_Unid', 'i_Preco', 'i_Vtotal']].copy()
                itens_ped_show.rename(columns={'i_codProd': 'Cód. Produto', 'i_NomeProd': 'Descrição', 'i_Qtdade': 'Qtd', 'i_Unid': 'UN', 'i_Preco': 'Preço Unit.', 'i_Vtotal': 'Total Item'}, inplace=True)
                
                itens_ped_show['Preço Unit.'] = itens_ped_show['Preço Unit.'].apply(lambda x: f"R$ {x:,.2f}")
                itens_ped_show['Total Item'] = itens_ped_show['Total Item'].apply(lambda x: f"R$ {x:,.2f}")
                st.dataframe(itens_ped_show, use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum pedido registrado nos últimos 6 meses para este cliente.")

# ==========================================
# ABA 3: PERFORMANCE DO VENDEDOR 
# ==========================================
with aba3:
    st.markdown("### 🏆 Cockpit de Gestão Comercial e Riscos")
    filiais_opcoes = ["TODAS", "0001", "0002", "0003", "0004", "0005", "0006"]
    filial_cockpit = st.selectbox("🎯 Filtro Principal de Visão:", filiais_opcoes, key="filial_cockpit_sel")
    
    if st.button("📊 Atualizar Cockpit Geral", type="primary", use_container_width=True, key="btn_cockpit"):
        with st.spinner("Mapeando carteira..."):
            try:
                query_perf = "SELECT Nome_Clien, Filial, i_Vtotal, Dt_Fatura, condPagto FROM PEDIDODEVENDA WHERE Status = 'Fat_OK'"
                params_perf = {}
                if st.session_state.perfil == "VENDEDOR":
                    query_perf += " AND Vendedor LIKE %(vend)s"
                    params_perf["vend"] = f"%{st.session_state.vendedor_nome}%"

                df_perf = pd.read_sql(query_perf, engine, params=params_perf)

                if df_perf.empty:
                    st.warning("Nenhum histórico faturado encontrado.")
                else:
                    df_perf['Data'] = pd.to_datetime(df_perf['Dt_Fatura'], format='%Y%m%d', errors='coerce')
                    df_perf['Mes_Ano'] = df_perf['Data'].dt.strftime('%Y-%m')
                    hoje = pd.to_datetime('today')
                    
                    def processar_pagamento(cond):
                        if pd.isna(cond) or not str(cond).strip(): return "OUTROS", 0.0
                        texto = str(cond).upper()
                        if "BOLETO" in texto: metodo = "BOLETO"
                        elif "PIX" in texto: metodo = "PIX"
                        elif "DEPOSITO" in texto or "DEPÓSITO" in texto: metodo = "DEPÓSITO"
                        elif "VISTA" in texto: metodo = "À VISTA"
                        else: metodo = "OUTROS"
                        numeros = re.findall(r'\d+', texto)
                        media_dias = sum(int(n) for n in numeros) / len(numeros) if numeros else 0.0
                        return metodo, media_dias

                    df_perf[['Metodo_Pagto', 'Prazo_Medio_Dias']] = df_perf['condPagto'].apply(lambda x: pd.Series(processar_pagamento(x)))
                    df_filt = df_perf if filial_cockpit == "TODAS" else df_perf[df_perf['Filial'] == filial_cockpit]
                    
                    if df_filt.empty:
                        st.error(f"Sem dados de faturamento para a filial {filial_cockpit}.")
                    else:
                        df_abc = df_filt.groupby('Nome_Clien')['i_Vtotal'].sum().reset_index().sort_values('i_Vtotal', ascending=False)
                        df_abc['Perc'] = df_abc['i_Vtotal'] / df_abc['i_Vtotal'].sum()
                        df_abc['Perc_Acumulado'] = df_abc['Perc'].cumsum()
                        df_abc['Classe'] = np.where(df_abc['Perc_Acumulado'] <= 0.8, 'A', np.where(df_abc['Perc_Acumulado'] <= 0.95, 'B', 'C'))
                        
                        col_r1, col_r2 = st.columns(2)
                        df_abc_count = df_abc.groupby('Classe').size().reset_index(name='Qtd')
                        fig_abc = px.pie(df_abc_count, values='Qtd', names='Classe', hole=0.5, title='Qtd Clientes Curva ABC', color='Classe', color_discrete_map={'A':'#10b981', 'B':'#f59e0b', 'C':'#64748b'})
                        col_r1.plotly_chart(fig_abc, use_container_width=True)
                        
                        df_filial_fat = df_filt.groupby('Filial')['i_Vtotal'].sum().reset_index()
                        fig_fil = px.pie(df_filial_fat, values='i_Vtotal', names='Filial', hole=0.5, title='Faturamento por Filial (%)')
                        col_r2.plotly_chart(fig_fil, use_container_width=True)

                        st.markdown("---")
                        st.markdown("#### 💰 Termômetro Financeiro (Global 6 Filiais)")
                        filiais_fixas = ['0001', '0002', '0003', '0004', '0005', '0006']
                        cols_prazo = st.columns(6)
                        for i, f in enumerate(filiais_fixas):
                            df_f = df_perf[df_perf['Filial'] == f]
                            prazo = df_f['Prazo_Medio_Dias'].mean() if not df_f.empty else 0
                            cols_prazo[i].metric(f"Prazo Filial {f}", f"{prazo:.0f} dias")

                        df_metodos = df_filt.groupby('Metodo_Pagto')['i_Vtotal'].sum().reset_index()
                        df_metodos['%'] = (df_metodos['i_Vtotal'] / df_metodos['i_Vtotal'].sum()) * 100
                        texto_metodos = " | ".join([f"**{row['Metodo_Pagto']}**: {row['%']:.1f}%" for _, row in df_metodos.iterrows()])
                        st.info(f"**Uso de Meios de Pagamento:** {texto_metodos}")
            except Exception as e:
                st.error(f"❌ Erro ao analisar o Cockpit: {e}")

# ==========================================
# ABA 4: CHATBOT IA COM CÉREBRO GEMINI TEXT-TO-SQL
# ==========================================
with aba4:
    st.markdown("### 🧠 Assistente Analítico (Cérebro Text-to-SQL)")
    st.markdown("A IA agora escreve as consultas de banco de dados do zero. Peça médias, rankings, maiores e menores.")
    st.markdown("💡 *Exemplos:* `Quais os 3 maiores clientes em faturamento?`, `Qual o maior pedido em aberto?`, `Me traga os itens mais vendidos e o preço médio.`")

    # Tenta configurar o Gemini na hora, caso não tenha sido configurado no topo
    try:
        import google.generativeai as genai
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        ia_configurada = True
    except Exception:
        ia_configurada = False

    if not ia_configurada:
        st.error("⚠️ A chave do Gemini não foi encontrada no Streamlit (Secrets). Adicione a GEMINI_API_KEY para a IA funcionar.")
    
    if "mensagens_chat_ia" not in st.session_state:
        st.session_state.mensagens_chat_ia = [
            {"role": "assistant", "content": "Fala chefe! O motor de Text-to-SQL está ligado com o Gemini 3. Agora eu entendo rankings, médias e valores unitários. Manda a bronca!", "df": None, "sql": None}
        ]

    for msg in st.session_state.mensagens_chat_ia:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("df") is not None:
                st.dataframe(pd.DataFrame(msg["df"]), use_container_width=True, hide_index=True)
            if msg.get("sql"):
                with st.expander("Ver o código SQL gerado pela IA"):
                    st.code(msg["sql"], language="sql")

    if prompt_ia := st.chat_input("Ex: traga a lista dos 3 maiores clientes...", key="chat_input_ia"):
        st.session_state.mensagens_chat_ia.append({"role": "user", "content": prompt_ia})
        with st.chat_message("user"):
            st.markdown(prompt_ia)

        if ia_configurada:
            with st.chat_message("assistant"):
                with st.spinner("🧠 O Gemini está desenhando a query SQL para sua pergunta..."):
                    try:
                        perfil_usuario = st.session_state.perfil
                        nome_usuario = st.session_state.vendedor_nome
                        
                        prompt_sistema = f"""
                        Você é um Analista de Dados Sênior especialista em MySQL para ERPs.
                        Sua missão é transformar a pergunta do usuário em uma única query SQL.
                        NÃO retorne NENHUM texto além da query SQL. Sem formatação markdown, sem crases, sem explicações.

                        Tabela principal: PEDIDODEVENDA
                        Colunas úteis:
                        - Nome_Clien (VARCHAR): Nome do Cliente
                        - i_NomeProd (VARCHAR): Nome ou descrição do Produto
                        - i_Preco (FLOAT): Preço Unitário do item
                        - Dt_Fatura (VARCHAR): Data de Faturamento (formato YYYYMMDD)
                        - Status (VARCHAR): Status do pedido ('Fat_OK' para faturados)
                        - Vendedor (VARCHAR): Nome do vendedor

                        REGRA DE SEGURANÇA OBRIGATÓRIA:
                        O usuário logado tem o perfil: {perfil_usuario} e nome: {nome_usuario}.
                        Se o perfil for 'VENDEDOR', você DEVE OBRIGATORIAMENTE adicionar a condição " Vendedor LIKE '%{nome_usuario}%' " na cláusula WHERE em todas as suas consultas.

                        DIRETRIZES DE QUERY COM FOCO NA SUA LÓGICA:
                        1. Quando o usuário pedir os **últimos preços de cada item para um cliente específico**, você DEVE buscar o produto, o preço da última data e a última data de faturamento de cada item.
                        2. Para estruturar isso sem quebrar a regra do GROUP BY do MySQL, use uma subconsulta ou ordene por data decrescente agrupando por item. 
                        Exemplo estrutural ideal:
                        SELECT i_NomeProd AS Produto, MAX(i_Preco) AS Ultimo_Preco, MAX(Dt_Fatura) AS Ultima_Data 
                        FROM PEDIDODEVENDA 
                        WHERE Status = 'Fat_OK' AND Nome_Clien LIKE '%NOME_DO_CLIENTE%' 
                        GROUP BY i_NomeProd ORDER BY Ultima_Data DESC;
                        3. Sempre use LIKE '%NOME%' para buscar o nome do cliente.
                        
                        Pergunta do usuário: "{prompt_ia}"
                        """
                    
                        model = genai.GenerativeModel('gemini-3-flash-preview')
                        resposta_gemini = model.generate_content(prompt_sistema)
                        
                        # Limpa qualquer resquício de formatação do texto da IA
                        query_sql = resposta_gemini.text.strip()
                        if query_sql.startswith("```sql"):
                            query_sql = query_sql[6:-3].strip()
                        elif query_sql.startswith("```"):
                            query_sql = query_sql[3:-3].strip()

                        # --- CORREÇÃO DO BUG DO PANDAS (Drible do sinal de %) ---
                        query_sql_segura = query_sql.replace('%', '%%')

                        # Executa a busca no E2DW baseada no SQL
                        df_res_ia = pd.read_sql(query_sql_segura, engine)

                        if df_res_ia.empty:
                            resposta_ia = "🤖 A query foi executada com sucesso, mas o banco de dados retornou vazio para essa combinação exata."
                            st.markdown(resposta_ia)
                            with st.expander("Ver o código SQL gerado pela IA"):
                                st.code(query_sql, language="sql")
                            
                            st.session_state.mensagens_chat_ia.append({
                                "role": "assistant", "content": resposta_ia, "df": None, "sql": query_sql
                            })
                        else:
                            # Formatação cosmética de colunas de moeda se a IA usar alias
                            for col in df_res_ia.columns:
                                if 'total' in col.lower() or 'preco' in col.lower() or 'preço' in col.lower() or 'valor' in col.lower() or 'média' in col.lower():
                                    df_res_ia[col] = df_res_ia[col].apply(lambda x: f"R$ {x:,.2f}" if isinstance(x, (int, float)) else x)
                            
                            resposta_ia = f"🤖 **Pronto!** Analisei a base e cheguei neste resultado:"
                            st.markdown(resposta_ia)
                            st.dataframe(df_res_ia, use_container_width=True, hide_index=True)
                            
                            with st.expander("Ver o código SQL gerado pela IA"):
                                st.code(query_sql, language="sql")

                            df_dict = df_res_ia.to_dict('records')
                            st.session_state.mensagens_chat_ia.append({
                                "role": "assistant", "content": resposta_ia, "df": df_dict, "sql": query_sql
                            })

                    except Exception as e:
                        erro_str = f"❌ Erro ao executar a query da IA: {e}"
                        st.error(erro_str)
                        st.session_state.mensagens_chat_ia.append({"role": "assistant", "content": erro_str, "df": None, "sql": None})

# --- FIM DO CÓDIGO ---
