"""Ratios du cycle d'exploitation et simulation à activité constante."""
from datetime import date, timedelta
import math
import streamlit as st
import pandas as pd


def money(value):
    return f'{value:,.0f} DH'.replace(',', ' ')


def calculate_ratios(stock, receivables, payables, sales, cost, purchases, days):
    values = (stock, receivables, payables, sales, cost, purchases, days)
    if not all(math.isfinite(float(v)) and v >= 0 for v in values) or days <= 0:
        raise ValueError('Les montants doivent être finis et positifs ou nuls ; la durée doit être positive.')
    dso = receivables / sales * days if sales > 0 else None
    dio = stock / cost * days if cost > 0 else None
    dpo = payables / purchases * days if purchases > 0 else None
    return {'DSO': dso, 'DIO': dio, 'DPO': dpo,
            'CCC': dso + dio - dpo if all(v is not None for v in (dso, dio, dpo)) else None}


def simulate_bfr(stock, receivables, payables, sales, cost, purchases, days, dso, dio, dpo):
    calculate_ratios(stock, receivables, payables, sales, cost, purchases, days)
    if min(sales, cost, purchases) <= 0:
        raise ValueError('La simulation nécessite des ventes, un coût des ventes et des achats strictement positifs.')
    if not all(math.isfinite(float(v)) and v >= 0 for v in (dso, dio, dpo)):
        raise ValueError('Les délais cibles doivent être finis et positifs ou nuls.')
    target_stock = cost / days * dio
    target_receivables = sales / days * dso
    target_payables = purchases / days * dpo
    baseline = stock + receivables - payables
    target = target_stock + target_receivables - target_payables
    return {'stock': target_stock, 'receivables': target_receivables, 'payables': target_payables,
            'baseline': baseline, 'target': target, 'released': baseline - target,
            'ccc': dso + dio - dpo,
            'stock_effect': stock - target_stock,
            'receivables_effect': receivables - target_receivables,
            'payables_effect': target_payables - payables}


def render_financial_analysis(stock, receivables, payables, source_label, source_id, demo_allowed):
    st.title('Analyse financière')
    st.caption('Comprendre les délais du cycle d’exploitation et tester leur effet sur le BFR.')
    st.caption(f'Situation disponible : {source_label}. Les hypothèses restent conservées pendant cette session.')
    defaults = {'start': date.today() - timedelta(days=364), 'end': date.today(),
                'sales': 0.0, 'cost': 0.0, 'purchases': 0.0,
                'basis': 'Soldes actuels — estimation',
                'stock': stock, 'receivables': receivables, 'payables': payables, 'demo': False}
    fields = list(defaults)
    if demo_allowed and st.button('Charger un exemple chiffré', key='finance_example'):
        example = dict(defaults, sales=365000.0, cost=219000.0, purchases=182500.0, demo=True)
        st.session_state['finance_inputs'] = example
        for field in fields:
            st.session_state.pop(f'fin_{field}', None)
        st.session_state.pop('finance_validated', None)
        st.session_state.pop('finance_scenario', None)
    saved = st.session_state.get('finance_inputs', defaults)
    # Widget keys may be cleaned up on other pages; durable session values are separate.
    for field in fields:
        st.session_state.setdefault(f'fin_{field}', saved[field])
    if saved['demo']:
        st.info('Exemple pédagogique : les flux préremplis sont fictifs. Modifiez-les pour vos propres calculs.')
    st.subheader('1. Définir la période et les flux')
    with st.form('finance_assumptions'):
        col1, col2 = st.columns(2)
        col1.date_input('Début de période', key='fin_start')
        col2.date_input('Fin de période', key='fin_end')
        st.caption('Renseignez les flux cumulés sur cette période. La durée utilise les jours calendaires, bornes incluses.')
        sales_col, cost_col, purchases_col = st.columns(3)
        sales_col.number_input('Ventes à crédit (DH)', min_value=0.0, step=1000.0, key='fin_sales',
            help='Même base fiscale que les créances : ventes TTC si les créances sont TTC, HT si elles sont HT. Exclure les ventes au comptant.')
        cost_col.number_input('Coût des ventes (DH)', min_value=0.0, step=1000.0, key='fin_cost',
            help='Coût des biens vendus, cohérent avec la valorisation des stocks. Ne pas saisir le chiffre d’affaires ni remplacer automatiquement par les achats.')
        purchases_col.number_input('Achats à crédit (DH)', min_value=0.0, step=1000.0, key='fin_purchases',
            help='Achats correspondant aux dettes fournisseurs étudiées, avec la même base HT ou TTC. Exclure les achats au comptant.')
        st.caption('Cohérence HT/TTC : utilisez la même base pour chaque couple créances/ventes et dettes/achats. '
                   'Les stocks et le coût des ventes doivent partager la même base de valorisation.')
        st.radio('Soldes utilisés pour les ratios',
                 ['Soldes actuels — estimation', 'Soldes moyens de la période — saisie manuelle'], key='fin_basis')
        with st.expander('Renseigner les soldes moyens si vous choisissez cette méthode'):
            st.caption('Ces champs sont utilisés uniquement avec « Soldes moyens ». '
                       'Saisissez vos moyennes de la période ; les valeurs initiales reprennent les soldes actuels.')
            avg1, avg2, avg3 = st.columns(3)
            avg1.number_input('Stock moyen (DH)', min_value=0.0, step=1000.0, key='fin_stock')
            avg2.number_input('Créances moyennes (DH)', min_value=0.0, step=1000.0, key='fin_receivables')
            avg3.number_input('Dettes moyennes (DH)', min_value=0.0, step=1000.0, key='fin_payables')
        submitted = st.form_submit_button('Calculer les ratios', type='primary')
    if submitted:
        params = {field: st.session_state[f'fin_{field}'] for field in fields}
        st.session_state['finance_inputs'] = params
        st.session_state.pop('finance_validated', None)
        st.session_state.pop('finance_scenario', None)
        if params['end'] < params['start']:
            st.error('La fin de période doit être postérieure ou égale au début.')
            return
        amounts = [params[k] for k in ['sales', 'cost', 'purchases', 'stock', 'receivables', 'payables']]
        if not all(math.isfinite(v) and v >= 0 for v in amounts):
            st.error('Renseignez des montants finis et positifs ou nuls.')
            return
        st.session_state['finance_validated'] = {'params': params, 'source_id': source_id}
        for key in ['target_dso', 'target_dio', 'target_dpo']:
            st.session_state.pop(key, None)
    validated = st.session_state.get('finance_validated')
    if validated is None:
        st.info('Renseignez les flux, puis cliquez sur « Calculer les ratios ». Aucun flux n’est déduit des soldes.')
        return
    if validated['source_id'] != source_id:
        st.warning('Les données importées ont changé. Vérifiez la période et les flux, puis recalculez les ratios.')
        return
    params = validated['params']
    days = (params['end'] - params['start']).days + 1
    average = params['basis'].startswith('Soldes moyens')
    base_stock, base_ar, base_ap = ((params['stock'], params['receivables'], params['payables'])
                                  if average else (stock, receivables, payables))
    sales, cost, purchases = params['sales'], params['cost'], params['purchases']
    ratios = calculate_ratios(base_stock, base_ar, base_ap, sales, cost, purchases, days)
    st.subheader('2. Lire les délais du cycle')
    st.caption(f"Calcul validé du {params['start']:%d/%m/%Y} au {params['end']:%d/%m/%Y} · {days} jours · {params['basis']}")
    if not average:
        st.caption('Ratios estimatifs : les soldes actuels remplacent les soldes moyens. '
                   'Les données actuelles doivent correspondre à la fin de la période choisie.')
    st.caption('Après toute modification des hypothèses ci-dessus, cliquez sur « Calculer les ratios » pour actualiser les résultats.')
    metrics = st.columns(4)
    for col, key, label in zip(metrics, ['DSO', 'DIO', 'DPO', 'CCC'],
            ['DSO · clients', 'DIO · stocks', 'DPO · fournisseurs', 'Cycle de trésorerie']):
        value = ratios[key]
        col.metric(label, 'Non calculable' if value is None else f'{value:.1f} j')
    st.write('Le **DSO** estime le délai d’encaissement ; le **DIO**, la durée de détention du stock ; '
             'le **DPO**, le délai de règlement des fournisseurs.')
    if ratios['CCC'] is not None:
        if ratios['CCC'] >= 0:
            st.info(f"Le cycle de conversion de trésorerie représente environ {ratios['CCC']:.1f} jours à financer, selon ces hypothèses.")
        else:
            st.info('Le cycle est négatif : selon ces hypothèses, les encaissements précèdent en moyenne les règlements fournisseurs. '
                    'Cela ne représente pas un solde bancaire.')
    with st.expander('Formules et méthode'):
        st.markdown('- DSO = Créances de référence ÷ Ventes à crédit × Nombre de jours\n'
                    '- DIO = Stocks de référence ÷ Coût des ventes × Nombre de jours\n'
                    '- DPO = Dettes fournisseurs de référence ÷ Achats à crédit × Nombre de jours\n'
                    '- Cycle de trésorerie = DSO + DIO − DPO')
        st.write('Un flux nul rend le ratio correspondant non calculable. '
                 'Ces ratios sont des estimations globales, pas la moyenne exacte des délais de chaque facture. '
                 'Leur appréciation dépend du secteur et de la saisonnalité.')
        st.markdown('[Méthode de référence : ACCA — Working capital management]'
                    '(https://www.accaglobal.com/gb/en/student/exam-support-resources/fundamentals-exams-study-resources/f9/technical-articles/wcm.html)')
    st.subheader('3. Simuler un changement de délais')
    if any(ratios[k] is None for k in ['DSO', 'DIO', 'DPO']):
        st.warning('Renseignez des ventes à crédit, un coût des ventes et des achats à crédit strictement positifs pour activer le simulateur.')
        return
    st.caption('Activité et prix constants : ajustez les délais pour estimer les soldes cibles et leur effet sur le BFR.')
    st.caption('Les délais fournisseurs supposent des conditions convenues ; le modèle ne tient pas compte '
               'des pénalités, escomptes, coûts de mise en œuvre ni du risque de rupture de stock.')
    scenario = st.session_state.get('finance_scenario', {})
    for key, ratio in [('target_dso', 'DSO'), ('target_dio', 'DIO'), ('target_dpo', 'DPO')]:
        st.session_state.setdefault(key, scenario.get(key, ratios[ratio]))
    with st.form('finance_simulation'):
        t1, t2, t3 = st.columns(3)
        t1.number_input('DSO cible (jours)', min_value=0.0, step=1.0, format='%.2f', key='target_dso')
        t2.number_input('DIO cible (jours)', min_value=0.0, step=1.0, format='%.2f', key='target_dio')
        t3.number_input('DPO cible (jours)', min_value=0.0, step=1.0, format='%.2f', key='target_dpo')
        simulated = st.form_submit_button('Simuler le scénario', type='primary')
    if simulated:
        targets = {k: st.session_state[k] for k in ['target_dso', 'target_dio', 'target_dpo']}
        if not all(math.isfinite(v) and v >= 0 for v in targets.values()):
            st.error('Les délais doivent être finis et positifs ou nuls.')
            return
        st.session_state['finance_scenario'] = targets
        scenario = targets
    if not scenario:
        st.caption('Les délais cibles sont initialisés aux délais de référence. Modifiez-les, puis lancez la simulation.')
        return
    result = simulate_bfr(base_stock, base_ar, base_ap, sales, cost, purchases, days,
                          scenario['target_dso'], scenario['target_dio'], scenario['target_dpo'])
    st.caption(f"Scénario calculé : DSO {scenario['target_dso']:.2f} j · DIO {scenario['target_dio']:.2f} j · "
               f"DPO {scenario['target_dpo']:.2f} j. Après modification des cibles, relancez la simulation.")
    m1, m2, m3 = st.columns(3)
    m1.metric('BFR moyen de référence' if average else 'BFR actuel de référence', money(result['baseline']))
    m2.metric('BFR cible simulé', money(result['target']))
    released = result['released']
    m3.metric('Trésorerie potentiellement libérée' if released >= -1e-7 else 'Besoin de financement supplémentaire',
              money(abs(released)))
    st.caption(f"Cycle cible : {result['ccc']:.1f} jours. L’effet de trésorerie est théorique et ponctuel ; ce n’est pas un bénéfice.")
    comparison = pd.DataFrame({
        'Composante': ['Stocks', 'Créances clients', 'Dettes fournisseurs'],
        'Référence (DH)': [base_stock, base_ar, base_ap],
        'Cible (DH)': [result['stock'], result['receivables'], result['payables']],
        'Effet sur la trésorerie (DH)': [result['stock_effect'], result['receivables_effect'], result['payables_effect']],
    })
    st.dataframe(comparison.round(2), use_container_width=True, hide_index=True)
    st.caption('Effet positif = trésorerie libérée ; effet négatif = financement supplémentaire. '
               'Une hausse des dettes réduit le BFR dans ce modèle.')
    st.bar_chart(pd.DataFrame({'BFR (DH)': [result['baseline'], result['target']]},
                 index=['Référence', 'Scénario']), color='#52cbbb', height=250)
