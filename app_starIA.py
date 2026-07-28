# ==========================================
# ABA 4: ASSISTENTE COMERCIAL IA (DINÂMICO)
# ==========================================
with aba4:
    st.markdown("### 🤖 Assistente Comercial Inteligente (IA Dinâmica)")
    st.markdown("Agora o assistente captura qualquer nome de cliente, filial e data direto da sua frase.")
    st.markdown("💡 *Exemplos:* `cliente agrobiologica faturados`, `pedidos abertos filial 0001 pirelli`, `faturamento julho de 2026`")

    if "mensagens_chat_ia" not in st.session_state:
        st.session_state.mensagens_chat_ia = [
            {"role": "assistant", "content": "Fala chefe! Agora o extrator lê qualquer nome de cliente que você digitar. Pode mandar o teste!"}
        ]

    for msg in st.session_state.mensagens_chat_ia:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt_ia := st.chat_input("Digite o comando (ex: cliente agrobiologica faturados)...", key="chat_input_ia"):
        st.session_state.mensagens_chat_ia.append({"role": "user", "content": prompt_ia})
        with st.chat_message("user"):
            st.markdown(prompt_ia)

        with st.chat_message("assistant"):
            with st.spinner("Varrendo o E2DW com extração dinâmica..."):
                try:
                    texto_lower = prompt_ia.lower()
                    
                    query_assistente = "SELECT PedVenda, Status, Nome_Clien, Cidade, Dt_Fatura, Data_Ped, i_Vtotal, i_NomeProd, TRANSPORTA, Filial FROM PEDIDODEVENDA WHERE 1=1"
                    params_assistente = {}

                    # 1. Segurança por Perfil
                    if st.session_state.perfil == "VENDEDOR":
                        query_assistente += " AND Vendedor LIKE %(v_log)s"
                        params_assistente["v_log"] = f"%{st.session_state.vendedor_nome}%"

                    # 2. Inteligência Dinâmica de Cliente (Captura o que vem após "cliente", "para", "da", "do")
                    match_cliente = re.search(r'(?:cliente|para|da|do)\s+([a-zA-ZÀ-ÿ0-9\s]+?)(?:\s+(?:faturado|aberto|filial|em|no|na|junho|julho|agosto|setembro|outubro|novembro|dezembro|janeiro|fevereiro|março|abril|maio|202|pedidos)|$)', texto_lower)
                    
                    # Se não achar com as preposições, tenta pegar a primeira palavra significativa se parecer nome próprio
                    cliente_busca = None
                    if match_cliente:
                        cliente_busca = match_cliente.group(1).strip()
                    else:
                        # Fallback: se digitou "agrobiologica" direto sem a palavra "cliente"
                        palavras_ignoradas = ["pedidos", "faturados", "abertos", "preciso", "dos", "do", "da", "de", "o", "a", "para", "com", "no", "na", "mes", "mês"]
                        tokens = [p for p in texto_lower.split() if p not in palavras_ignoradas and not p.startswith("202") and not p.isdigit()]
                        if tokens:
                            cliente_busca = tokens[0] # Pega o termo principal (ex: agrobiologica)

                    if cliente_busca and len(cliente_busca) > 2:
                        query_assistente += " AND Nome_Clien LIKE %(cli_busca)s"
                        params_assistente["cli_busca"] = f"%{cliente_busca.upper()}%"

                    # 3. Inteligência de Filial
                    match_filial = re.search(r'filial\s*0*([1-6])', texto_lower)
                    if match_filial:
                        num_filial = match_filial.group(1).zfill(4)
                        query_assistente += " AND Filial = %(filial_busca)s"
                        params_assistente["filial_busca"] = num_filial

                    # 4. Inteligência de Status
                    if "aberto" in texto_lower:
                        query_assistente += " AND Status = 'Aberto'"
                    elif "faturado" in texto_lower or "fat_ok" in texto_lower:
                        query_assistente += " AND Status = 'Fat_OK'"

                    # 5. Inteligência de Mês e Ano
                    meses_map = {
                        "janeiro": "01", "fevereiro": "02", "março": "03", "marco": "03",
                        "abril": "04", "maio": "05", "junho": "06", "julho": "07",
                        "agosto": "08", "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12"
                    }
                    
                    ano_match = re.search(r'202[6-9]', texto_lower)
                    ano_encontrado = ano_match.group(0) if ano_match else "2026"

                    mes_encontrado = None
                    for nome_mes, num_mes in meses_map.items():
                        if nome_mes in texto_lower:
                            mes_encontrado = num_mes
                            break

                    if mes_encontrado:
                        competencia = f"{ano_encontrado}{mes_encontrado}"
                        query_assistente += " AND (Dt_Fatura LIKE %(comp)s OR Data_Ped LIKE %(comp)s)"
                        params_assistente["comp"] = f"{competencia}%"

                    query_assistente += " LIMIT 250;"
                    df_res_ia = pd.read_sql(query_assistente, engine, params=params_assistente)

                    if df_res_ia.empty:
                        resposta_ia = f"Não encontrei registros para o termo **'{cliente_busca.upper() if cliente_busca else 'informado'}'** com esses filtros."
                        st.markdown(resposta_ia)
                    else:
                        total_valor = df_res_ia['i_Vtotal'].sum()
                        total_pedidos = df_res_ia['PedVenda'].nunique()
                        
                        cli_info = f" do cliente **{cliente_busca.upper()}**" if cliente_busca else ""
                        filial_info = f" (Filial {num_filial})" if match_filial else ""
                        
                        resposta_ia = f"Encontrei **{total_pedidos} pedido(s)**{cli_info}{filial_info}, totalizando **R$ {total_valor:,.2f}**."
                        st.markdown(resposta_ia)

                        df_show_ia = df_res_ia[['PedVenda', 'Filial', 'Status', 'Nome_Clien', 'Data_Ped', 'Dt_Fatura', 'i_Vtotal']].drop_duplicates()
                        df_show_ia.rename(columns={'PedVenda': 'Nº Pedido', 'Filial': 'Filial', 'Status': 'Status', 'Nome_Clien': 'Cliente', 'Data_Ped': 'Emissão', 'Dt_Fatura': 'Faturamento', 'i_Vtotal': 'Valor Total'}, inplace=True)
                        df_show_ia['Valor Total'] = df_show_ia['Valor Total'].apply(lambda x: f"R$ {x:,.2f}")
                        st.dataframe(df_show_ia, use_container_width=True, hide_index=True)

                    st.session_state.mensagens_chat_ia.append({"role": "assistant", "content": resposta_ia})

                except Exception as e:
                    erro_str = f"❌ Erro ao processar: {e}"
                    st.error(erro_str)
                    st.session_state.mensagens_chat_ia.append({"role": "assistant", "content": erro_str})
