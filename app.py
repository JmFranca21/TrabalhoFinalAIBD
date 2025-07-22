import streamlit as st
import pandas as pd
from astrapy import DataAPIClient

# --- 1. Configuração da Conexão (Data API) ---
st.set_page_config(layout="wide")

ASTRA_DB_API_ENDPOINT = st.secrets["ASTRA_DB_API_ENDPOINT"]
ASTRA_DB_APPLICATION_TOKEN = st.secrets["ASTRA_DB_APPLICATION_TOKEN"]
KEYSPACE_NAME = "gestao_co2"


# Nomes de todas as suas coleções
ALL_COLLECTIONS = [
    "cidade", "emissor", "estado", "especie", "funcionario", "localizacao", "organizacao", "tipo_emissor", "emissores_por_cidade", "organizacoes_por_estado"
]

# Inicializa o cliente de conexão
try:
    client = DataAPIClient(ASTRA_DB_APPLICATION_TOKEN)
    db = client.get_database_by_api_endpoint(ASTRA_DB_API_ENDPOINT, keyspace=KEYSPACE_NAME)
    st.sidebar.success("Conectado ao Astra DB via Data API!")
except Exception as e:
    st.sidebar.error(f"Erro ao conectar: {e}")
    st.stop()

# --- 2. Funções de Apoio ---

@st.cache_data(ttl=300) # Cache para não recarregar a cada ação
def carregar_itens_para_selecao(_collection_name):
    try:
        collection = db.get_collection(_collection_name)
        display_field = "descricao" if _collection_name == "localizacao" else "nome"
        
        # Verifica se o campo de exibição existe em pelo menos um documento
        sample_doc = collection.find_one()
        if sample_doc and display_field not in sample_doc:
            display_field = "_id"
        
        resultados = list(collection.find(projection={"_id": 1, display_field: 1}))
        return {item.get(display_field, item['_id']): item['_id'] for item in resultados}
    except Exception:
        return {}

# --- 3. Interface Principal ---

st.title("Dashboard de Gestão de CO2")
st.sidebar.header("Modo de Operação")
modo = st.sidebar.radio("Escolha uma ação:", ("Consultas Específicas", "Visualizar Coleção Completa"))

# --- MODO DE CONSULTAS ESPECÍFICAS ---
if modo == "Consultas Específicas":
    st.sidebar.header("Consultas de Relacionamento")

    query_map = {
        "Buscar Emissores por Cidade": ("cidade", "emissores_por_cidade", "id_cidade"),
        "Buscar Cidades por Emissor": ("emissor", "cidades_por_emissor", "id_emissor"),
        "Buscar Organizações por Estado": ("estado", "organizacoes_por_estado", "id_estado"),
    }
    
    consulta_escolhida = st.sidebar.selectbox("Selecione o tipo de consulta:", query_map.keys())
    
    entidade_origem, tabela_consulta, id_coluna_filtro = query_map[consulta_escolhida]

    st.header(f"Consulta: {consulta_escolhida}")
    mapa_ids = carregar_itens_para_selecao(entidade_origem)

    if mapa_ids:
        item_selecionado = st.selectbox(f"Selecione um(a) {entidade_origem}:", mapa_ids.keys())
        
        if st.button(f"Buscar dados para '{item_selecionado}'"):
            id_selecionado = mapa_ids[item_selecionado]
            with st.spinner("Buscando..."):
                collection = db.get_collection(tabela_consulta)
                resultados = list(collection.find(filter={id_coluna_filtro: id_selecionado}))
            
            if resultados:
                df = pd.DataFrame(resultados).drop(columns=[id_coluna_filtro, "_id"], errors='ignore')
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum resultado encontrado para esta seleção.")
    else:
        st.warning(f"Não foi possível carregar dados da entidade '{entidade_origem}'. Verifique se a coleção existe e está populada.")

# --- MODO DE VISUALIZAÇÃO COMPLETA ---
elif modo == "Visualizar Coleção Completa":
    st.header("Visualização de Coleções Completas")
    
    collection_escolhida = st.selectbox("Selecione a coleção que deseja visualizar:", ALL_COLLECTIONS)
    
    if st.button(f"Carregar dados de '{collection_escolhida}'"):
        try:
            with st.spinner(f"Carregando coleção '{collection_escolhida}'..."):
                collection = db.get_collection(collection_escolhida)
                # O .find() sem argumentos busca todos os documentos
                resultados = list(collection.find())
            
            if resultados:
                st.dataframe(pd.DataFrame(resultados), use_container_width=True, hide_index=True)
            else:
                st.info(f"A coleção '{collection_escolhida}' está vazia.")
        except Exception as e:
            st.error(f"Não foi possível carregar a coleção: {e}")