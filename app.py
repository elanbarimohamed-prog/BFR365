import streamlit as st
import pandas as pd
import math
from io import BytesIO
from html import escape
from datetime import date, timedelta

st.set_page_config(page_title='BFR360 | Tableau de bord', page_icon='📊',
                   layout='wide', initial_sidebar_state='expanded')

st.markdown("""
<style>
.stApp { background: #0d1422; color: #e9eff8; }
[data-testid="stHeader"] { background: #0d1422; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px; }
[data-testid="stSidebar"] { background: #121d2e; }
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"],
[data-testid="stMetricLabel"] { color: #e9eff8; }
[data-testid="stCaptionContainer"] { color: #a4b3c9; }
h1, h2, h3 { color: #e9eff8 !important; }
[data-testid="stMetric"] { background: #172235; border: 1px solid #293951;
 border-radius: 16px; padding: 22px; }
[data-testid="stMetricValue"] { color: #f4f8ff; font-weight: 700; }
[data-testid="stPopoverButton"], [data-testid="stSidebarCollapsedControl"] button,
[data-testid="collapsedControl"] button, [data-testid="stSidebarCollapseButton"] button {
 background: #22334c !important; color: #f0f5ff !important;
 border: 1px solid #506480 !important; border-radius: 10px; }
[data-testid="stPopoverButton"] p { color: #f0f5ff !important; }
[data-testid="stPopoverBody"] { background: #172235; color: #e9eff8; }
[data-testid="stPopoverButton"]:hover,
[data-testid="stSidebarCollapsedControl"] button:hover,
[data-testid="stSidebarCollapseButton"] button:hover { background: #314765 !important; }
.hero { background: linear-gradient(110deg, #172942, #173942);
 border: 1px solid #2a4556; padding: 26px 32px; border-radius: 18px; margin: 12px 0 24px; }
.hero .eyebrow { color: #7bd9cc; font-size: 12px; letter-spacing: 2px; font-weight: 700; }
.hero h1 { font-size: clamp(26px, 4vw, 38px); padding: 10px 0; }
.hero p { color: #bdcddd; margin: 0; }
.section-label { color: #8fa8c3; text-transform: uppercase; font-size: 12px;
 letter-spacing: 1.5px; font-weight: 700; margin-top: 24px; }
.state-card { background: #172235; border: 1px solid #293951; padding: 22px;
 border-radius: 14px; margin: 12px 0; min-height: 145px; }
.state-card strong { font-size: 22px; color: #eef5ff; }
.state-card p { color: #b5c5d9; margin: 8px 0 0; }
.alert-card { padding: 16px 20px; border: 1px solid #293951; border-left: 4px solid;
 border-radius: 10px; background: #172235; margin: 10px 0; }
.alert-card.critical { border-left-color: #ff7182; }
.alert-card.high { border-left-color: #ffb366; }
.alert-card.watch { border-left-color: #e3cd79; }
.alert-card .priority { font-size: 11px; font-weight: 700; letter-spacing: 1px; }
.critical .priority { color: #ff9ca7; }
.high .priority { color: #ffca91; }
.watch .priority { color: #e3cd79; }
.alert-card strong { color: #edf3fd; }
.alert-card p { color: #b5c5d9; margin: 6px 0 0; }

/* A narrow, persistent navigation rail on desktop; native drawer on mobile. */
[data-testid="stSidebar"] { min-width: 184px !important; max-width: 184px !important;
 background: #101827; border-right: 1px solid #293951; }
[data-testid="stSidebarUserContent"] { padding: 18px 12px; }
[data-testid="stSidebar"] [data-testid="stButton"] button {
 width: 100%; min-height: 66px; border-radius: 12px; text-align: left;
 background: #172235; color: #dce7f5; border: 1px solid #293951; margin-bottom: 8px; }
[data-testid="stSidebar"] [data-testid="stButton"] button:hover {
 background: #243851; border-color: #52cbbb; }
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {
 background: #21443f; border-color: #52cbbb; color: #a9f6e9; }
.nav-brand { font-size: 22px; font-weight: 800; letter-spacing: 1px;
 color: #80e0cf; padding: 12px 4px 24px; }
.nav-foot { font-size: 11px; color: #8fa8c3; padding: 24px 4px; }
</style>
""", unsafe_allow_html=True)

def money(value):
    return f'{value:,.0f} DH'.replace(',', ' ')


def read_csv(upload):
    # Accepte les CSV séparés par une virgule ou un point-virgule.
    return pd.read_csv(upload, sep=None, engine='python', encoding='utf-8-sig')


def numeric(df, columns):
    for col in columns:
        df[col] = pd.to_numeric(df[col], errors='raise')
        if df[col].isna().any() or not df[col].map(math.isfinite).all():
            raise ValueError(f'La colonne {col} contient une valeur manquante ou non finie.')
        if (df[col] < 0).any():
            raise ValueError(f'La colonne {col} doit contenir des valeurs positives ou nulles.')


def validate_history(df):
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='raise').dt.normalize()
    if df.empty or df['Date'].isna().any():
        raise ValueError('L’historique doit contenir au moins une date valide.')
    if df['Date'].duplicated().any():
        raise ValueError('Utilisez une seule ligne de soldes par date.')
    numeric(df, ['Stocks', 'Créances clients', 'Dettes fournisseurs'])
    df['BFR'] = df['Stocks'] + df['Créances clients'] - df['Dettes fournisseurs']
    return df.sort_values('Date').reset_index(drop=True)


def build_alerts(stocks_df, clients_df, suppliers_df, today):
    alerts = []
    for _, row in stocks_df.iterrows():
        qty, threshold = row['Quantité'], row['Seuil minimum']
        if qty == 0:
            alerts.append((0, 0, 'critical', 'CRITIQUE · RUPTURE',
                f"{row['Produit']} : stock épuisé",
                'Réapprovisionnement à traiter en priorité.'))
        elif qty <= threshold:
            alerts.append((2, qty / threshold if threshold else 0, 'watch', 'À SURVEILLER · STOCK',
                f"{row['Produit']} : stock faible",
                f"{qty:g} unités disponibles pour un seuil de {threshold:g}. Préparer le réapprovisionnement."))
    for df, name, kind, action in [
        (clients_df, 'Client', 'CRÉANCE', 'Relancer le client.'),
        (suppliers_df, 'Fournisseur', 'DETTE', 'Vérifier le règlement avec le fournisseur.')]:
        for _, row in df.iterrows():
            if not row['Payée'] and row['Échéance'] < today:
                days = (today - row['Échéance']).days
                alerts.append((1, -days, 'high', f'PRIORITÉ HAUTE · {kind}',
                    f"{row[name]} : {money(row['Montant (DH)'])} en retard",
                    f"Échéance du {row['Échéance']:%d/%m/%Y} · {days} jour(s) de retard. {action}"))
    return sorted(alerts, key=lambda item: (item[0], item[1]))


stocks_demo = pd.DataFrame([
    {'Produit':'Farine','Quantité':20,'Seuil minimum':30,'Coût unitaire (DH)':90},
    {'Produit':'Huile','Quantité':50,'Seuil minimum':20,'Coût unitaire (DH)':120},
    {'Produit':'Sucre','Quantité':12,'Seuil minimum':15,'Coût unitaire (DH)':75},
    {'Produit':'Riz','Quantité':80,'Seuil minimum':25,'Coût unitaire (DH)':60},
])
clients_demo = pd.DataFrame([
    {'Client':'Client A','Montant (DH)':15000,'Échéance':date.today()-timedelta(days=12),'Payée':False},
    {'Client':'Client B','Montant (DH)':24000,'Échéance':date.today()+timedelta(days=15),'Payée':False},
    {'Client':'Client C','Montant (DH)':9000,'Échéance':date.today()-timedelta(days=4),'Payée':True},
])
fournisseurs_demo = pd.DataFrame([
    {'Fournisseur':'Fournisseur X','Montant (DH)':17000,'Échéance':date.today()+timedelta(days=8),'Payée':False},
    {'Fournisseur':'Fournisseur Y','Montant (DH)':11000,'Échéance':date.today()-timedelta(days=3),'Payée':False},
])


if 'active_view' not in st.session_state:
    st.session_state.active_view = 'Dashboard'


def navigate(view):
    st.session_state.active_view = view


if 'nav_compact' not in st.session_state:
    st.session_state.nav_compact = False


def toggle_navigation():
    st.session_state.nav_compact = not st.session_state.nav_compact


compact = st.session_state.nav_compact
rail_width = 76 if compact else 184
# Replace Streamlit's hide action with a compact mode that retains navigation.
st.markdown(f"""
<style>
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
[data-testid="stSidebarHeader"] {{ display: none !important; }}
[data-testid="stSidebar"] {{
    width: {rail_width}px !important;
    min-width: {rail_width}px !important;
    max-width: {rail_width}px !important;
    flex: 0 0 {rail_width}px !important;
    transform: none !important;
    margin-left: 0 !important;
    position: relative !important;
    left: 0 !important;
    visibility: visible !important;
    display: block !important;
}}
[data-testid="stSidebarUserContent"] {{ padding: 16px 8px !important; }}
[data-testid="stSidebar"] [data-testid="stButton"] button {{
    min-height: 50px; padding: 8px 4px; justify-content: center;
}}
[data-testid="stSidebar"] [data-testid="stButton"] button p {{
    font-size: {'24px' if compact else '15px'};
}}
.nav-brand {{ font-size: {'17px' if compact else '22px'}; text-align: center; padding: 12px 0 22px; }}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.button('›' if compact else '‹  Replier', key='toggle_navigation',
              help='Déplier la navigation' if compact else 'Replier en mode icônes',
              on_click=toggle_navigation, use_container_width=True)
    st.markdown(f'<div class="nav-brand">{"BFR" if compact else "BFR360"}</div>', unsafe_allow_html=True)
    for label, icon in [('Infos', 'ⓘ'), ('Données', '▤'),
                        ('Dashboard', '▦'), ('Évolution historique', '↗')]:
        st.button(icon if compact else f'{icon}  {label}', key=f'nav_{label}',
                  type='primary' if st.session_state.active_view == label else 'secondary',
                  use_container_width=True, on_click=navigate, args=(label,), help=label)
    if not compact:
        st.markdown('<div class="nav-foot">PILOTAGE FINANCIER<br>Montants en DH</div>', unsafe_allow_html=True)

view = st.session_state.active_view


def remember_upload(widget_key, storage_key):
    uploaded = st.session_state.get(widget_key)
    st.session_state[storage_key] = (
        {'name': uploaded.name, 'bytes': uploaded.getvalue()} if uploaded is not None else None)


def current_file(storage_key):
    saved = st.session_state.get(storage_key)
    return BytesIO(saved['bytes']) if saved is not None else None


def forget_upload(storage_key, widget_key):
    st.session_state.pop(storage_key, None)
    st.session_state.pop(widget_key, None)


if view == 'Infos':
    st.title('Infos')
    st.markdown('### Comprendre le BFR')
    st.markdown('**BFR simplifié = Stocks + Créances clients − Dettes fournisseurs**')
    st.write("Un BFR positif représente un besoin de financement du cycle d’exploitation. "
             "Un BFR négatif représente une ressource issue de ce cycle.")
    st.caption("Une analyse comptable complète prend aussi en compte les autres postes "
               "d’exploitation pertinents. Le BFR n’est pas le solde bancaire.")
    st.markdown('**Historique :** une ligne par date, avec les soldes de stocks, '
                'créances non payées et dettes non payées à cette date.')
    st.caption('Prototype pédagogique • montants en dirhams (DH).')

    st.markdown('### Se repérer dans BFR360')
    st.write('**Données** : importer les stocks, créances, dettes et soldes historiques.')
    st.write('**Dashboard** : consulter la situation actuelle et les alertes prioritaires.')
    st.write('**Évolution historique** : suivre les quatre indicateurs dans le temps.')
    st.caption('Les imports sont conservés pendant cette session de navigation. '
               'Ils ne constituent pas une sauvegarde permanente après fermeture ou redémarrage.')
    st.stop()

if view == 'Données':
    st.title('Données')
    st.caption('Importez vos CSV, puis utilisez la barre de gauche pour consulter vos indicateurs.')
    upload_definitions = [
        ('Stocks (CSV)', 'stocks', 'Produit, Quantité, Seuil minimum, Coût unitaire (DH)'),
        ('Créances clients (CSV)', 'clients', 'Client, Montant (DH), Échéance, Payée'),
        ('Dettes fournisseurs (CSV)', 'fournisseurs', 'Fournisseur, Montant (DH), Échéance, Payée'),
        ('Historique des soldes (CSV)', 'historique', 'Date, Stocks, Créances clients, Dettes fournisseurs'),
    ]
    for offset in (0, 2):
        cols = st.columns(2)
        for col, (label, name, columns) in zip(cols, upload_definitions[offset:offset+2]):
            with col:
                storage_key, widget_key = f'saved_{name}', f'upload_{name}'
                st.subheader(label.replace(' (CSV)', ''))
                st.file_uploader(label, type='csv', key=widget_key,
                    on_change=remember_upload, args=(widget_key, storage_key))
                st.caption(f'Colonnes : {columns}')
                saved = st.session_state.get(storage_key)
                if saved is not None:
                    st.caption(f"Fichier actif : {saved['name']}")
                    st.button('Retirer ce fichier', key=f'remove_{name}',
                        on_click=forget_upload, args=(storage_key, widget_key))
                else:
                    st.caption('Aucun fichier importé.')
    with st.expander('Formats et modèle d’historique'):
        st.write('CSV UTF-8 séparé par une virgule ou un point-virgule. '
                 'Dates : AAAA-MM-JJ. Payée : True ou False. Montants en DH.')
        st.write('Historique : une ligne par date avec les soldes des stocks, des créances '
                 'non payées et des dettes non payées à cette date.')
        st.download_button('Télécharger le modèle CSV',
            data='Date;Stocks;Créances clients;Dettes fournisseurs\n2026-01-31;18000;42000;28000\n2026-02-28;16000;38000;27000\n',
            file_name='modele_historique.csv', mime='text/csv')
        st.caption('Deux lignes fictives à remplacer par vos valeurs.')

stocks = current_file('saved_stocks')
clients = current_file('saved_clients')
fournisseurs = current_file('saved_fournisseurs')
historique = current_file('saved_historique')

try:
    s = read_csv(stocks) if stocks is not None else stocks_demo.copy()
    c = read_csv(clients) if clients is not None else clients_demo.copy()
    f = read_csv(fournisseurs) if fournisseurs is not None else fournisseurs_demo.copy()
    numeric(s, ['Quantité', 'Seuil minimum', 'Coût unitaire (DH)'])
    if 'Produit' not in s.columns:
        raise ValueError('Colonne Produit manquante.')
    for df, name in [(c, 'Client'), (f, 'Fournisseur')]:
        if name not in df.columns:
            raise ValueError(f'Colonne {name} manquante.')
        numeric(df, ['Montant (DH)'])
        df['Échéance'] = pd.to_datetime(df['Échéance'], errors='raise').dt.date
        if df['Échéance'].isna().any():
            raise ValueError('Une échéance est manquante.')
        df['Payée'] = df['Payée'].astype(str).str.strip().str.lower().map(
            {'true':True, 'false':False, 'vrai':True, 'faux':False, '1':True, '0':False})
        if df['Payée'].isna().any():
            raise ValueError('La colonne Payée doit contenir True ou False.')
except (ValueError, KeyError, TypeError, pd.errors.ParserError, UnicodeError) as e:
    st.error(f'Erreur dans les données CSV : {e}')
    st.stop()

stock_value = float((s['Quantité'] * s['Coût unitaire (DH)']).sum())
receivables = float(c.loc[~c['Payée'], 'Montant (DH)'].sum())
payables = float(f.loc[~f['Payée'], 'Montant (DH)'].sum())
bfr = stock_value + receivables - payables
sources = [stocks is not None, clients is not None, fournisseurs is not None]
source_label = ('Données de démonstration' if not any(sources) else
                'Données importées' if all(sources) else 'Données mixtes : imports et exemples')

if view == 'Données':
    st.caption(f'{source_label} · aperçu de la situation actuelle')
    s_display = s.copy()
    s_display['Valeur (DH)'] = s_display['Quantité'] * s_display['Coût unitaire (DH)']
    with st.expander('Consulter le détail des opérations', expanded=False):
        stock_tab, clients_tab, suppliers_tab = st.tabs(['Stocks', 'Clients', 'Fournisseurs'])
        with stock_tab:
            st.dataframe(s_display, use_container_width=True, hide_index=True)
        with clients_tab:
            st.dataframe(c, use_container_width=True, hide_index=True)
        with suppliers_tab:
            st.dataframe(f, use_container_width=True, hide_index=True)

    if historique is not None:
        try:
            st.subheader('Aperçu de l’historique')
            st.dataframe(validate_history(read_csv(historique)), use_container_width=True, hide_index=True)
        except (ValueError, KeyError, TypeError, pd.errors.ParserError, UnicodeError) as e:
            st.error(f'Historique invalide : {e}')
    st.stop()

if view == 'Évolution historique':
    st.subheader('Évolution du cycle d’exploitation')
    history = None
    if historique is not None:
        try:
            history = validate_history(read_csv(historique))
            st.caption('Historique importé · indépendant des cartes de situation actuelle.')
        except (ValueError, KeyError, TypeError, pd.errors.ParserError, UnicodeError) as e:
            st.error(f'Historique invalide : {e}')
    elif not any(sources):
        history = validate_history(pd.DataFrame({
            'Date': pd.date_range(end=pd.Timestamp.today().normalize().replace(day=1), periods=12, freq='MS'),
            'Stocks': [18000,17500,19200,18100,16500,17200,15800,14900,15200,14100,13800,13500],
            'Créances clients': [46000,44500,47000,43000,42000,44500,41000,39500,42000,40000,40500,39000],
            'Dettes fournisseurs': [27000,28000,29500,28500,28000,29000,27500,28000,29500,28500,29000,28000],
        }))
        st.caption('DÉMONSTRATION · 12 situations mensuelles fictives, distinctes de la situation actuelle.')
    else:
        st.info('Importez un historique dans le panneau Données pour afficher une évolution réelle. '
                'Les fichiers de situation actuelle ne permettent pas de reconstituer le passé.')
    if history is not None:
        period = st.selectbox('Période', ['Tout l’historique', '6 derniers mois', '3 derniers mois'])
        filtered = history.copy()
        if period != 'Tout l’historique':
            months = 6 if period.startswith('6') else 3
            cutoff = history['Date'].max() - pd.DateOffset(months=months)
            filtered = history.loc[history['Date'] > cutoff].copy()
        chart_data = filtered.set_index('Date')
        st.caption(f"Du {filtered['Date'].iloc[0]:%d/%m/%Y} au {filtered['Date'].iloc[-1]:%d/%m/%Y} · montants en DH")
        if len(filtered) < 2:
            st.info('Une seule observation : au moins deux dates sont nécessaires pour tracer une évolution.')
        panels = [('BFR', '#52cbbb'), ('Stocks', '#78afff'),
                  ('Créances clients', '#c2a0ff'), ('Dettes fournisseurs', '#ffbf80')]
        for offset in (0, 2):
            cols = st.columns(2)
            for col, (name, color) in zip(cols, panels[offset:offset+2]):
                with col:
                    st.markdown(f'#### {name}')
                    change = filtered[name].iloc[-1] - filtered[name].iloc[0]
                    st.metric('Dernier solde de la période', money(filtered[name].iloc[-1]),
                              delta=money(change) if len(filtered) > 1 else None,
                              delta_color='off')
                    if len(filtered) > 1:
                        st.line_chart(chart_data[[name]], color=color, height=240)
        with st.expander('Consulter les valeurs historiques'):
            st.dataframe(filtered, use_container_width=True, hide_index=True)

    st.stop()

st.markdown('<div class="hero"><div class="eyebrow">BFR360 · PILOTAGE FINANCIER</div>'
            '<h1>Votre cycle d’exploitation, en un regard.</h1>'
            '<p>Suivez vos besoins de financement, vos stocks et vos échéances.</p></div>',
            unsafe_allow_html=True)
st.markdown('<div class="section-label">Situation actuelle</div>', unsafe_allow_html=True)
st.caption(f'{source_label} · Échéances évaluées au {date.today():%d/%m/%Y}')
m1, m2, m3, m4 = st.columns(4)
m1.metric('BFR simplifié', money(bfr))
m2.metric('Valeur des stocks', money(stock_value))
m3.metric('Créances clients', money(receivables))
m4.metric('Dettes fournisseurs', money(payables))


low = int((s['Quantité'] <= s['Seuil minimum']).sum())
empty = int((s['Quantité'] == 0).sum())
left, right = st.columns(2)
with left:
    st.subheader('État actuel du BFR')
    bfr_label = 'Besoin de financement' if bfr > 0 else 'Ressource d’exploitation' if bfr < 0 else 'Équilibre du cycle'
    st.markdown(f'<div class="state-card"><strong>{bfr_label}</strong>'
                f'<p>{money(abs(bfr))} · situation calculée à partir des soldes actuels.</p>'
                '<p>À apprécier au regard de l’activité et du financement disponible.</p></div>',
                unsafe_allow_html=True)
    st.bar_chart(pd.DataFrame({'Montant (DH)': [stock_value, receivables, -payables]},
                 index=['Stocks', 'Créances', 'Dettes']), color='#52cbbb', height=230)
    st.caption('Composition actuelle en DH · les dettes réduisent le besoin.')
with right:
    st.subheader('État actuel des stocks')
    stock_label = 'Rupture de stock' if empty else 'Réapprovisionnement à prévoir' if low else 'Stocks au-dessus des seuils'
    if s.empty:
        stock_label = 'Aucun produit renseigné'
    st.markdown(f'<div class="state-card"><strong>{stock_label}</strong>'
                f'<p>{len(s)} référence(s) · {low} au seuil ou en dessous · {empty} en rupture.</p>'
                f'<p>Valeur totale : {money(stock_value)}.</p></div>', unsafe_allow_html=True)
    s_display = s.copy()
    s_display['Valeur (DH)'] = s_display['Quantité'] * s_display['Coût unitaire (DH)']
    s_display['Statut'] = s_display.apply(lambda r: 'Rupture' if r['Quantité'] == 0 else
        'À réapprovisionner' if r['Quantité'] <= r['Seuil minimum'] else 'Disponible', axis=1)
    st.dataframe(s_display[['Produit', 'Quantité', 'Seuil minimum', 'Statut']],
                 use_container_width=True, hide_index=True)

st.subheader('Alertes prioritaires')
st.caption('Ordre : ruptures de stock → paiements en retard (les plus anciens d’abord) '
           '→ stocks faibles (les plus proches de la rupture d’abord).')
alerts = build_alerts(s, c, f, date.today())
if not alerts:
    st.success('Aucune alerte selon les règles de stock et d’échéance.')
for _, _, severity, priority, title, detail in alerts:
    st.markdown(f'<div class="alert-card {severity}"><div class="priority">{escape(priority)}</div>'
                f'<strong>{escape(title)}</strong><p>{escape(detail)}</p></div>', unsafe_allow_html=True)

