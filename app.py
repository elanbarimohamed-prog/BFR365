import streamlit as st
import pandas as pd
import math
from datetime import date, timedelta

st.set_page_config(page_title='BFR360 | Tableau de bord', page_icon='📊',
                   layout='wide', initial_sidebar_state='collapsed')

st.markdown("""
<style>
.stApp { background: #f4f7fb; color: #182b49; }
[data-testid="stHeader"] { background: #f4f7fb; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px; }
[data-testid="stSidebar"] { background: #eef2f8; }
[data-testid="stMetric"] { background: #ffffff; border: 1px solid #e0e7f0;
 border-radius: 16px; padding: 22px; box-shadow: 0 4px 16px #152b4910; }
[data-testid="stMetricLabel"] { color: #52657e; }
[data-testid="stMetricValue"] { color: #182b49; font-weight: 700; }
.hero { background: linear-gradient(110deg, #132c4c, #1b5364);
 padding: 30px 34px; border-radius: 20px; margin: 12px 0 25px; color: white; }
.hero .eyebrow { color: #89ded0; font-size: 12px; letter-spacing: 2px; font-weight: 700; }
.hero h1 { color: white; font-size: clamp(26px, 4vw, 40px); padding: 10px 0; }
.hero p { color: #d6e5ef; margin: 0; }
.section-label { color: #52718a; text-transform: uppercase; font-size: 12px;
 letter-spacing: 1.5px; font-weight: 700; margin-top: 24px; }
</style>
""", unsafe_allow_html=True)

with st.popover('ⓘ Infos'):
    st.markdown('### Comprendre le BFR')
    st.markdown('**BFR simplifié = Stocks + Créances clients − Dettes fournisseurs**')
    st.write("Un BFR positif représente un besoin de financement du cycle d’exploitation. "
             "Un BFR négatif représente une ressource issue de ce cycle.")
    st.caption("Une analyse comptable complète prend aussi en compte les autres postes "
               "d’exploitation pertinents. Le BFR n’est pas le solde bancaire.")
    st.markdown('**Historique :** une ligne par date, avec les soldes de stocks, '
                'créances non payées et dettes non payées à cette date.')
    st.caption('Prototype pédagogique • montants en dirhams (DH).')

st.markdown('<div class="hero"><div class="eyebrow">BFR360 · PILOTAGE FINANCIER</div>'
            '<h1>Votre cycle d’exploitation, en un regard.</h1>'
            '<p>Suivez vos besoins de financement, vos stocks et vos échéances.</p></div>',
            unsafe_allow_html=True)
st.caption('Ouvrez ou masquez le panneau Données avec la flèche en haut à gauche.')


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

with st.sidebar:
    st.header('Données')
    st.caption('Cliquez sur la flèche en haut du panneau pour le masquer.')
    st.write('Importez vos fichiers CSV ou explorez les exemples intégrés.')
    stocks = st.file_uploader('Stocks (CSV)', type='csv')
    clients = st.file_uploader('Créances clients (CSV)', type='csv')
    fournisseurs = st.file_uploader('Dettes fournisseurs (CSV)', type='csv')
    st.divider()
    historique = st.file_uploader('Historique des soldes (CSV)', type='csv')
    with st.expander('Format de l’historique'):
        st.write('Colonnes : Date, Stocks, Créances clients, Dettes fournisseurs. '
                 'Montants en DH ; dates au format AAAA-MM-JJ. '
                 'Chaque ligne représente les soldes à cette date, pas les flux de la période.')
        st.download_button('Télécharger le modèle CSV',
            data='Date;Stocks;Créances clients;Dettes fournisseurs\n2026-01-31;18000;42000;28000\n2026-02-28;16000;38000;27000\n',
            file_name='modele_historique.csv', mime='text/csv')
        st.caption('Le modèle contient deux lignes fictives à remplacer.')

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
st.markdown('<div class="section-label">Situation actuelle</div>', unsafe_allow_html=True)
st.caption(f'{source_label} · Échéances évaluées au {date.today():%d/%m/%Y}')
m1, m2, m3, m4 = st.columns(4)
m1.metric('BFR simplifié', money(bfr))
m2.metric('Valeur des stocks', money(stock_value))
m3.metric('Créances clients', money(receivables))
m4.metric('Dettes fournisseurs', money(payables))

st.markdown('<div class="section-label">Tableau de bord</div>', unsafe_allow_html=True)
left, right = st.columns([2, 1])
with left:
    st.subheader('Évolution du BFR')
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
        if len(filtered) > 1:
            st.line_chart(chart_data[['BFR']], color='#128578', height=310)
            delta = filtered['BFR'].iloc[-1] - filtered['BFR'].iloc[0]
            st.caption(f"Du {filtered['Date'].iloc[0]:%d/%m/%Y} au {filtered['Date'].iloc[-1]:%d/%m/%Y} "
                       f"· Variation du BFR : {'+' if delta > 0 else ''}{money(delta)}")
        else:
            st.info('Une seule observation sur cette période : au moins deux sont nécessaires pour tracer une évolution.')
        with st.expander('Voir les composantes et les valeurs historiques'):
            if len(filtered) > 1:
                st.line_chart(chart_data[['Stocks', 'Créances clients', 'Dettes fournisseurs']], height=260)
            st.dataframe(filtered, use_container_width=True, hide_index=True)
with right:
    st.subheader('Composition actuelle')
    st.caption('Montants en DH · les dettes réduisent le besoin.')
    st.bar_chart(pd.DataFrame({'Montant (DH)': [stock_value, receivables, -payables]},
                 index=['Stocks', 'Créances', 'Dettes']), color='#268caa', height=310)
    late = c.loc[(~c['Payée']) & (c['Échéance'] < date.today()), 'Montant (DH)'].sum()
    low = int((s['Quantité'] <= s['Seuil minimum']).sum())
    st.caption(f'{low} produit(s) au seuil ou en dessous · {money(late)} de créances en retard')

st.subheader('Détail des opérations')
stock_tab, clients_tab, suppliers_tab, alert_tab = st.tabs(['📦 Stocks','👥 Clients','🚚 Fournisseurs','🔔 Alertes'])
with stock_tab:
    s_display=s.copy()
    s_display['Valeur (DH)']=s_display['Quantité']*s_display['Coût unitaire (DH)']
    s_display['Statut']=s_display.apply(lambda r:'⚠️ À réapprovisionner' if r['Quantité']<=r['Seuil minimum'] else '✅ OK',axis=1)
    st.dataframe(s_display,use_container_width=True,hide_index=True)
with clients_tab:
    st.dataframe(c,use_container_width=True,hide_index=True)
with suppliers_tab:
    st.dataframe(f,use_container_width=True,hide_index=True)
with alert_tab:
    count=0
    for _,r in s.iterrows():
        if r['Quantité']<=r['Seuil minimum']:
            st.warning(f"Stock faible : {r['Produit']} ({r['Quantité']} unités, seuil {r['Seuil minimum']}).")
            count+=1
    for _,r in c.iterrows():
        if not r['Payée'] and r['Échéance']<date.today():
            st.error(f"Créance en retard : {r['Client']} — {r['Montant (DH)']:,.0f} DH, échéance {r['Échéance']}.")
            count+=1
    for _,r in f.iterrows():
        if not r['Payée'] and r['Échéance']<date.today():
            st.warning(f"Dette fournisseur échue : {r['Fournisseur']} — {r['Montant (DH)']:,.0f} DH.")
            count+=1
    if count==0:
        st.success('Aucune alerte sur ces règles.')
