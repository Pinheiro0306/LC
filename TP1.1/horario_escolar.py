# /// script
# dependencies = ["marimo"]
# requires-python = ">=3.14"
# ///

import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo


@app.cell
def _():
    import pandas as pd
    from ortools.sat.python import cp_model

    # Lê os ficheiros CSV da pasta 'dados'
    try:
        turmas_df = pd.read_csv("dados/turmas.csv")
        disciplinas_df = pd.read_csv("dados/disciplinas.csv")
        salas_df = pd.read_csv("dados/salas.csv")
        excecoes_df = pd.read_csv("dados/disponibilidade_excecoes.csv")
        print("Ficheiros lidos com sucesso!")
    except FileNotFoundError as e:
        print(f"Erro ao ler ficheiro: {e}. Verifica se a pasta 'dados' está no sítio certo.")

    # Deixar o nome de uma variável na última linha faz com que o Marimo mostre a tabela
    turmas_df
    return cp_model, disciplinas_df, excecoes_df, pd, salas_df, turmas_df


@app.cell
def _(cp_model, disciplinas_df, excecoes_df, salas_df, turmas_df):
    # 1. Configurações base
    dias = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex']
    periodos = [1, 2, 3, 4, 5]

    lista_turmas = turmas_df['turma'].tolist()
    lista_disciplinas = disciplinas_df.to_dict('records')

    # 2. Iniciar o Modelo
    model = cp_model.CpModel()

    # Dicionários para as variáveis
    x = {} # x[turma, disciplina, dia, periodo] -> 1 se tem aula
    b = {} # b[turma, disciplina, dia, periodo] -> 1 se INICIA um bloco duplo

    # Criar as variáveis
    for t in lista_turmas:
        for disc in lista_disciplinas:
            d = disc['disciplina']
            duplo = (disc['duplo_periodo'] == 'sim')
    
            for dia in dias:
                for p in periodos:
                    x[(t, d, dia, p)] = model.NewBoolVar(f'x_{t}_{d}_{dia}_{p}')
            
                    # Variável de bloco b só existe para disciplinas de duplo período 
                    # e não pode começar no último período do dia
                    if duplo and p < max(periodos):
                        b[(t, d, dia, p)] = model.NewBoolVar(f'b_{t}_{d}_{dia}_{p}')

    # 3. Adicionar Restrições (R1 a R4)
    for t in lista_turmas:
        for dia in dias:
            for p in periodos:
                # R1: Uma turma não pode ter mais do que 1 aula em simultâneo
                model.AddAtMostOne(x[(t, disc['disciplina'], dia, p)] for disc in lista_disciplinas)

        for disc in lista_disciplinas:
            d = disc['disciplina']
            carga = disc['carga_semanal']
            duplo = (disc['duplo_periodo'] == 'sim')
    
            # R2: Carga semanal exata por (turma, disciplina)
            model.Add(sum(x[(t, d, dia, p)] for dia in dias for p in periodos) == carga)
    
            for dia in dias:
                if not duplo:
                    # R3 (simples): Máximo de 1 aula por dia para disciplinas normais
                    model.Add(sum(x[(t, d, dia, p)] for p in periodos) <= 1)
                else:
                    # R3/R4 (duplos): Lógica dos blocos
                    # Máximo de 1 bloco a iniciar por dia
                    model.Add(sum(b[(t, d, dia, p)] for p in periodos if p < max(periodos)) <= 1)
            
                    # Relacionar o x (ter aula) com o b (início do bloco)
                    # x[p] tem de ser igual a b[p] + b[p-1] (com cuidado nos extremos)
                    for p in periodos:
                        termos = []
                        if p < max(periodos):
                            termos.append(b[(t, d, dia, p)])     # Bloco começou agora
                        if p > min(periodos):
                            termos.append(b[(t, d, dia, p-1)])   # Bloco começou no período anterior
                
                        model.Add(x[(t, d, dia, p)] == sum(termos))

    print("Variáveis criadas e restrições R1 a R4 adicionadas com sucesso!")
    # 1. Configurações base
    dias = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex']
    periodos = [1, 2, 3, 4, 5]

    lista_turmas = turmas_df['turma'].tolist()
    lista_disciplinas = disciplinas_df.to_dict('records')

    # Dicionários auxiliares
    prof_da_disciplina = {d['disciplina']: d['professor'] for d in lista_disciplinas}
    sala_da_disciplina = {
        d['disciplina']: d['sala_especial'] if isinstance(d['sala_especial'], str) and d['sala_especial'].strip() != '' else 'normal' 
        for d in lista_disciplinas
    }
    professores = set(prof_da_disciplina.values())

    capacidades = {}
    for _, row in salas_df.iterrows():
        if row['tipo'] == 'normal':
            capacidades['normal'] = capacidades.get('normal', 0) + row['quantidade']
        else:
            capacidades[row['sala']] = row['quantidade']

    # 2. Iniciar o Modelo e Variáveis
    model = cp_model.CpModel()
    x = {} # x[turma, disciplina, dia, periodo]
    b = {} # b[turma, disciplina, dia, periodo]

    for t in lista_turmas:
        for disc in lista_disciplinas:
            d = disc['disciplina']
            duplo = (disc['duplo_periodo'] == 'sim')
            for dia in dias:
                for p in periodos:
                    x[(t, d, dia, p)] = model.NewBoolVar(f'x_{t}_{d}_{dia}_{p}')
                    if duplo and p < max(periodos):
                        b[(t, d, dia, p)] = model.NewBoolVar(f'b_{t}_{d}_{dia}_{p}')

    # 3. Restrições R1 a R4
    for t in lista_turmas:
        for dia in dias:
            for p in periodos:
                # R1: Uma turma não pode ter mais do que 1 aula em simultâneo
                model.AddAtMostOne(x[(t, disc['disciplina'], dia, p)] for disc in lista_disciplinas)

        for disc in lista_disciplinas:
            d = disc['disciplina']
            carga = disc['carga_semanal']
            duplo = (disc['duplo_periodo'] == 'sim')
    
            # R2: Carga semanal exata
            model.Add(sum(x[(t, d, dia, p)] for dia in dias for p in periodos) == carga)
    
            for dia in dias:
                if not duplo:
                    # R3: Máximo de 1 aula por dia
                    model.Add(sum(x[(t, d, dia, p)] for p in periodos) <= 1)
                else:
                    # R3/R4: Lógica dos blocos duplos
                    model.Add(sum(b[(t, d, dia, p)] for p in periodos if p < max(periodos)) <= 1)
                    for p in periodos:
                        termos = []
                        if p < max(periodos): termos.append(b[(t, d, dia, p)])
                        if p > min(periodos): termos.append(b[(t, d, dia, p-1)])
                        model.Add(x[(t, d, dia, p)] == sum(termos))

    # 4. Restrições R5, R6 e R7
    for prof in professores:
        for dia in dias:
            for p in periodos:
                # R5: Professor não dá duas aulas em simultâneo
                model.AddAtMostOne(
                    x[(t, disc['disciplina'], dia, p)] 
                    for t in lista_turmas 
                    for disc in lista_disciplinas if disc['professor'] == prof
                )

    # R6: Indisponibilidades
    for _, row in excecoes_df.iterrows():
        prof = row['professor']
        dia = row['dia']
        p = row['periodo']
        for t in lista_turmas:
            for disc in lista_disciplinas:
                if disc['professor'] == prof:
                    model.Add(x[(t, disc['disciplina'], dia, p)] == 0)

    # R7: Lotação das salas
    for dia in dias:
        for p in periodos:
            for tipo_sala, cap in capacidades.items():
                model.Add(
                    sum(
                        x[(t, disc['disciplina'], dia, p)] 
                        for t in lista_turmas 
                        for disc in lista_disciplinas if sala_da_disciplina[disc['disciplina']] == tipo_sala
                    ) <= cap
                )

    print("Restrições R1 a R7 adicionadas com sucesso!")
    return (
        capacidades,
        dias,
        lista_disciplinas,
        lista_turmas,
        model,
        periodos,
        professores,
        sala_da_disciplina,
        x,
    )


@app.cell
def _(
    cp_model,
    dias,
    lista_disciplinas,
    lista_turmas,
    model,
    periodos,
    professores,
    x,
):
    # 1. Variáveis para o objetivo O1 (Buracos)
    buracos_totais = []

    for pr in professores:
        for d_obj in dias:
            w = {}      
            antes = {}  
            depois = {} 
            buraco = {} 
    
            for per in periodos:
                # w[per] = soma das aulas do professor naquele período (no máximo 1)
                w[per] = model.NewBoolVar(f'w_{pr}_{d_obj}_{per}')
                aulas_prof_periodo = [
                    x[(t, disc['disciplina'], d_obj, per)]
                    for t in lista_turmas
                    for disc in lista_disciplinas if disc['professor'] == pr
                ]
                model.Add(w[per] == sum(aulas_prof_periodo))
        
                antes[per] = model.NewBoolVar(f'antes_{pr}_{d_obj}_{per}')
                depois[per] = model.NewBoolVar(f'depois_{pr}_{d_obj}_{per}')
                buraco[per] = model.NewBoolVar(f'buraco_{pr}_{d_obj}_{per}')
                buracos_totais.append(buraco[per])
    
            for per in periodos:
                # Lógica do 'antes': máximo de todos os 'w' anteriores
                if per > min(periodos):
                    model.AddMaxEquality(antes[per], [w[k] for k in periodos if k < per])
                else:
                    model.Add(antes[per] == 0)
            
                # Lógica do 'depois': máximo de todos os 'w' seguintes
                if per < max(periodos):
                    model.AddMaxEquality(depois[per], [w[k] for k in periodos if k > per])
                else:
                    model.Add(depois[per] == 0)
        
                # Um período é buraco se: antes=1 E depois=1 E w=0
                model.Add(buraco[per] >= antes[per] + depois[per] - w[per] - 1)

    # Dizemos ao modelo para minimizar a soma de todos os buracos detetados
    model.Minimize(sum(buracos_totais))

    # 2. Resolver o modelo!
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0 

    print("A procurar o melhor horário. Isto pode demorar alguns segundos...")
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"✅ Horário encontrado! Status: {solver.StatusName(status)}")
        print(f"🎯 Número total de buracos dos professores: {int(solver.ObjectiveValue())}")
    else:
        print("❌ Não foi encontrada nenhuma solução. O problema pode ser impossível com estes dados.")
    return solver, status


@app.cell
def _(
    cp_model,
    dias,
    display,
    lista_disciplinas,
    lista_turmas,
    pd,
    periodos,
    sala_da_disciplina,
    solver,
    status,
    x,
):
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        # 1. Extrair os resultados: recolher os tempos em que x == 1
        aulas_marcadas = []

        # Nomes completamente novos para evitar choques com células anteriores
        for t_out in lista_turmas:
            for d_out in dias:
                for p_out in periodos:
                    for disc_out in lista_disciplinas:
                        nome_disc = disc_out['disciplina']
                        # Verifica se o solver decidiu colocar esta aula aqui
                        if solver.Value(x[(t_out, nome_disc, d_out, p_out)]) == 1:
                            aulas_marcadas.append({
                                'Turma': t_out,
                                'Dia': d_out,
                                'Período': p_out,
                                'Disciplina': nome_disc,
                                'Professor': disc_out['professor'],
                                'Sala': sala_da_disciplina[nome_disc]
                            })

        # 2. Converter para DataFrame (o pd já existe na memória desde a célula 1)
        df_horario = pd.DataFrame(aulas_marcadas)

        # 3. Mostrar as tabelas formatadas
        for t_print in lista_turmas:
            print(f"\n{'='*40}")
            print(f" HORÁRIO DA TURMA {t_print}")
            print(f"{'='*40}")
    
            df_turma = df_horario[df_horario['Turma'] == t_print]
    
            tabela = df_turma.pivot(
                index='Período', 
                columns='Dia', 
                values='Disciplina'
            ).reindex(columns=dias).fillna('---')
    
            try:
                display(tabela)
            except NameError:
                print(tabela)
    return (df_horario,)


@app.cell
def _(
    capacidades,
    cp_model,
    dias,
    excecoes_df,
    lista_disciplinas,
    lista_turmas,
    pd,
    periodos,
    professores,
    sala_da_disciplina,
    solver,
    x,
):
    import time

    # 1. Guardar o H0 (estado atual das variáveis do horário original)
    h0_valores = {}
    for t_h0 in lista_turmas:
        for d_h0 in dias:
            for p_h0 in periodos:
                for disc_h0 in lista_disciplinas:
                    nome = disc_h0['disciplina']
                    h0_valores[(t_h0, nome, d_h0, p_h0)] = solver.Value(x[(t_h0, nome, d_h0, p_h0)])
            
    total_aulas_h0 = sum(h0_valores.values())

    # 2. Preparar os dados_v2 (Prof. Ana indisponível Sexta aos períodos 4 e 5)
    novas_ex = pd.DataFrame([
        {'professor': 'Prof. Ana', 'dia': 'Sex', 'periodo': 4},
        {'professor': 'Prof. Ana', 'dia': 'Sex', 'periodo': 5}
    ])
    excecoes_v2_df = pd.concat([excecoes_df, novas_ex], ignore_index=True)

    # 3. Iniciar NOVO Modelo para o H1 (Incremental)
    m2 = cp_model.CpModel()
    x2 = {}
    b2 = {}

    for t_i in lista_turmas:
        for disc_i in lista_disciplinas:
            d_i = disc_i['disciplina']
            duplo_i = (disc_i['duplo_periodo'] == 'sim')
            for dia_i in dias:
                for p_i in periodos:
                    x2[(t_i, d_i, dia_i, p_i)] = m2.NewBoolVar(f'x2_{t_i}_{d_i}_{dia_i}_{p_i}')
                    if duplo_i and p_i < max(periodos):
                        b2[(t_i, d_i, dia_i, p_i)] = m2.NewBoolVar(f'b2_{t_i}_{d_i}_{dia_i}_{p_i}')

    # Reaplicar R1 a R4
    for t_i in lista_turmas:
        for dia_i in dias:
            for p_i in periodos:
                m2.AddAtMostOne(x2[(t_i, disc_i['disciplina'], dia_i, p_i)] for disc_i in lista_disciplinas)
        
        for disc_i in lista_disciplinas:
            d_i = disc_i['disciplina']
            carga_i = disc_i['carga_semanal']
            duplo_i = (disc_i['duplo_periodo'] == 'sim')
    
            m2.Add(sum(x2[(t_i, d_i, dia_i, p_i)] for dia_i in dias for p_i in periodos) == carga_i)
            for dia_i in dias:
                if not duplo_i:
                    m2.Add(sum(x2[(t_i, d_i, dia_i, p_i)] for p_i in periodos) <= 1)
                else:
                    m2.Add(sum(b2[(t_i, d_i, dia_i, p_i)] for p_i in periodos if p_i < max(periodos)) <= 1)
                    for p_i in periodos:
                        termos_i = []
                        if p_i < max(periodos): termos_i.append(b2[(t_i, d_i, dia_i, p_i)])
                        if p_i > min(periodos): termos_i.append(b2[(t_i, d_i, dia_i, p_i-1)])
                        m2.Add(x2[(t_i, d_i, dia_i, p_i)] == sum(termos_i))

    # Reaplicar R5, R6 (agora com excecoes_v2_df) e R7
    for prof_i in professores:
        for dia_i in dias:
            for p_i in periodos:
                m2.AddAtMostOne(
                    x2[(t_i, disc_i['disciplina'], dia_i, p_i)] 
                    for t_i in lista_turmas 
                    for disc_i in lista_disciplinas if disc_i['professor'] == prof_i
                )

    for _, row_i in excecoes_v2_df.iterrows():
        for t_i in lista_turmas:
            for disc_i in lista_disciplinas:
                if disc_i['professor'] == row_i['professor']:
                    m2.Add(x2[(t_i, disc_i['disciplina'], row_i['dia'], row_i['periodo'])] == 0)

    for dia_i in dias:
        for p_i in periodos:
            for tipo_s_i, cap_i in capacidades.items():
                m2.Add(sum(
                    x2[(t_i, disc_i['disciplina'], dia_i, p_i)] 
                    for t_i in lista_turmas 
                    for disc_i in lista_disciplinas if sala_da_disciplina[disc_i['disciplina']] == tipo_s_i
                ) <= cap_i)

    # 4. Estratégia Incremental e Objetivo de Minimizar Alterações
    aulas_mantidas = []
    for chave, valor_h0 in h0_valores.items():
        # A) Injetar Hint para o solver começar a partir do H0
        m2.AddHint(x2[chave], valor_h0)

        # B) Maximizar a manutenção das aulas que já estavam marcadas no H0
        if valor_h0 == 1:
            aulas_mantidas.append(x2[chave])

    m2.Maximize(sum(aulas_mantidas))

    # 5. Resolver e Medir Tempo
    solver2 = cp_model.CpSolver()
    solver2.parameters.repair_hint = True
    solver2.parameters.max_time_in_seconds = 30.0

    inicio_inc = time.time()
    status2 = solver2.Solve(m2)
    tempo_inc = time.time() - inicio_inc

    if status2 == cp_model.OPTIMAL or status2 == cp_model.FEASIBLE:
        aulas_perdidas = total_aulas_h0 - solver2.ObjectiveValue()
        print(f"✅ H1 Incremental resolvido com sucesso!")
        print(f"⏱️ Tempo de execução: {tempo_inc:.4f} segundos.")
        print(f"🔄 Aulas alteradas face a H0: {int(aulas_perdidas)} de {int(total_aulas_h0)} totais.")
    else:
        print("❌ Não foi encontrada solução para o H1.")
    return


@app.cell
def _(df_horario, excecoes_df, pd):
    def verificar_horario(df, df_excecoes):
        erros = []
    
        # R1: Turmas com mais de uma aula ao mesmo tempo
        sobreposicoes_turma = df.groupby(['Turma', 'Dia', 'Período']).size()
        for index, contagem in sobreposicoes_turma.items():
            if contagem > 1:
                erros.append(f"Erro R1: A turma {index[0]} tem {contagem} aulas na {index[1]} ao período {index[2]}.")
            
        # R5: Professores com mais de uma aula ao mesmo tempo
        sobreposicoes_prof = df.groupby(['Professor', 'Dia', 'Período']).size()
        for index, contagem in sobreposicoes_prof.items():
            if contagem > 1:
                erros.append(f"Erro R5: O {index[0]} tem {contagem} aulas na {index[1]} ao período {index[2]}.")
            
        # R6: Professores a dar aulas em períodos de indisponibilidade
        for _, row in df.iterrows():
            prof = row['Professor']
            dia = row['Dia']
            per = row['Período']
        
            indisponivel = df_excecoes[
                (df_excecoes['professor'] == prof) & 
                (df_excecoes['dia'] == dia) & 
                (df_excecoes['periodo'] == per)
            ]
            if not indisponivel.empty:
                erros.append(f"Erro R6: {prof} a dar aula num período de exceção ({dia}, {per}).")

        if not erros:
            print("✅ O horário passou na verificação independente!")
        else:
            for erro in erros:
                print("❌", erro)

    # 1. Testar o horário válido gerado pelo solver
    print("--- TESTE 1: Horário Válido (H0) ---")
    verificar_horario(df_horario, excecoes_df)

    # 2. Testar por mutação (estragar o horário propositadamente)
    print("\n--- TESTE 2: Horário Mutado (Estragado) ---")
    df_mutado = df_horario.copy()

    # Forçar uma aula do Prof. Eduardo à Segunda-feira de manhã (período 1), onde ele está indisponível (R6)
    # e que vai chocar com a aula que a turma já lá tem (R1)
    aula_proibida = pd.DataFrame([{
        'Turma': '7ºA', 'Dia': 'Seg', 'Período': 1, 
        'Disciplina': 'Educação Física', 'Professor': 'Prof. Eduardo', 'Sala': 'Ginásio'
    }])
    df_mutado = pd.concat([df_mutado, aula_proibida], ignore_index=True)

    verificar_horario(df_mutado, excecoes_df)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
