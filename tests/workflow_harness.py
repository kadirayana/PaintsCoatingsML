"""
Uçtan uca kullanıcı akışı betiği (manuel/CI dışı doğrulama aracı)
=================================================================
Gerçek Tkinter arayüzünü, gerçek (geçici) bir veritabanıyla bir kullanıcı gibi
sürer ve her adımın sonucunu veritabanından kontrol eder:

    Proje oluştur → Hammadde ekle → Formülasyon kaydet → Ağaçta gör →
    Test sonucu gir → Arka plan ML eğitimi → Optimizasyon → Karşılaştırma →
    Editöre yükle → Dashboard → Varyasyon sil → Dil değiştir

Kullanım (ekran gerekir; Linux'ta xvfb-run ile):
    python tests/workflow_harness.py
Çıkış kodu: 0 = tüm adımlar geçti, 1 = en az bir adım başarısız.
"""
import os
import sys
import time
import random
import shutil
import tempfile
import traceback
import configparser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = tempfile.mkdtemp(prefix='pfai_harness_')
# Uygulama dizinini kopyala ki gerçek model/veri dosyalarına dokunulmasın
for item in ('app', 'src', 'lang', 'config.ini'):
    src = os.path.join(ROOT, item)
    dst = os.path.join(WORK, item)
    (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, dst)
os.makedirs(os.path.join(WORK, 'assets', 'models'))
os.makedirs(os.path.join(WORK, 'data_storage'))
sys.path.insert(0, WORK)
os.chdir(WORK)

import tkinter as tk  # noqa: E402
from tkinter import messagebox, simpledialog  # noqa: E402

# Modal diyalogları otomatik yanıtla, ne sorulduğunu kaydet
DIALOGS = []
ANSWERS = {'askstring': [], 'askyesno': True, 'askyesnocancel': True}


def _record(kind, ret):
    def f(*a, **k):
        DIALOGS.append((kind, a[:2]))
        return ret() if callable(ret) else ret
    return f


for name in ('showinfo', 'showwarning', 'showerror'):
    setattr(messagebox, name, _record(name, None))
messagebox.askyesno = _record('askyesno', lambda: ANSWERS['askyesno'])
messagebox.askyesnocancel = _record('askyesnocancel', lambda: ANSWERS['askyesnocancel'])
simpledialog.askstring = _record('askstring', lambda: ANSWERS['askstring'].pop(0) if ANSWERS['askstring'] else None)

from src.data_handlers.local_db_manager import LocalDBManager  # noqa: E402
from app.ui_components import PaintFormulationApp  # noqa: E402

RESULTS = []
CALLBACK_ERRORS = []


def check(name, cond, detail=''):
    RESULTS.append((name, bool(cond), detail))
    print(('PASS ' if cond else 'FAIL ') + name + (f'  [{detail}]' if detail and not cond else ''))


def step(name):
    def deco(fn):
        def run(*a, **k):
            try:
                return fn(*a, **k)
            except Exception as e:
                traceback.print_exc()
                check(name + ' (istisna)', False, f'{type(e).__name__}: {e}')
        return run
    return deco


class Net:
    def check_connection(self):
        return False

    def __getattr__(self, n):
        return lambda *a, **k: False


db = LocalDBManager(os.path.join(WORK, 'data_storage', 'db.sqlite'))
db.initialize()
cfg = configparser.ConfigParser()
cfg.read(os.path.join(WORK, 'config.ini'), encoding='utf-8')
app = PaintFormulationApp(config=cfg, db_manager=db, network_checker=Net(), app_dir=WORK)
root = app.root
root.report_callback_exception = lambda exc, val, tb: CALLBACK_ERRORS.append(
    ''.join(traceback.format_exception(exc, val, tb)))
if hasattr(app, 'learning_controller') and app.learning_controller:
    app.learning_controller._debounce_delay = 0.1


def pump(seconds=0.3):
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        time.sleep(0.02)


def q(sql, args=()):
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]


pump()

# ---------------------------------------------------------------- 1. Proje
ANSWERS['askstring'] = ['Proje A']
app.sidebar._open_new_project_dialog()
pump()
projects = q("SELECT * FROM projects WHERE is_active = 1")
check('Proje oluşturuldu', len(projects) == 1)
PID = projects[0]['id'] if projects else None
tree_items = app.sidebar.tree.get_children()
check('Proje ağaçta görünüyor', any('Proje A' in app.sidebar.tree.item(i, 'text') for i in tree_items))

# Projeyi ağaçtan seç (kullanıcı tıklaması)
app.sidebar.tree.selection_set(f'p_{PID}')
app.sidebar._on_select(None)
pump()
check('Proje seçimi bağlama aktarıldı', app.context.project_id == PID)

# ---------------------------------------------------------------- 2. Hammaddeler
MATS = [('Akrilik Reçine', 'R-100', 'binder', 12.0, 50),
        ('TiO2 Rutil', 'P-200', 'pigment', 25.0, 100),
        ('Kalsit', 'F-300', 'filler', 2.0, 100),
        ('Su', 'S-400', 'solvent', 0.1, 0),
        ('Dispersan', 'A-500', 'additive', 40.0, 40)]
for name, code, cat, price, solid in MATS:
    mid = db.add_material({'name': name, 'code': code, 'category': cat, 'unit_price': price})
    with db.get_connection() as conn:
        conn.execute('UPDATE materials SET solid_content = ? WHERE id = ?', (solid, mid))
app._on_material_list_change()
pump()
check('Hammaddeler eklendi', len(db.get_all_materials()) == 5)


# ---------------------------------------------------------------- 3. Formülasyonlar
@step('Formülasyon kaydı')
def save_formulation(code, concept, binder, pigment, filler):
    ed = app.formulation_editor
    ed._clear_form()
    ed.project_combo.set('Proje A')
    ed._on_project_selected()
    ed.formula_code_entry.insert(0, code)
    ed.formula_name_entry.insert(0, concept)
    water = 100 - binder - pigment - filler - 1
    ed.grid.load_data([
        {'material_code': 'R-100', 'material_name': 'Akrilik Reçine', 'weight': binder, 'unit_price': 12.0, 'solid_content': 50},
        {'material_code': 'P-200', 'material_name': 'TiO2 Rutil', 'weight': pigment, 'unit_price': 25.0},
        {'material_code': 'F-300', 'material_name': 'Kalsit', 'weight': filler, 'unit_price': 2.0},
        {'material_code': 'S-400', 'material_name': 'Su', 'weight': water, 'unit_price': 0.1, 'solid_content': 0},
        {'material_code': 'A-500', 'material_name': 'Dispersan', 'weight': 1, 'unit_price': 40.0, 'solid_content': 40},
    ])
    DIALOGS.clear()
    ed._save()
    pump()


random.seed(42)
RECIPES = []
for i in range(6):
    b, p, f = random.uniform(25, 45), random.uniform(10, 25), random.uniform(5, 20)
    concept = 'İç Cephe Mat' if i < 3 else 'Dış Cephe Parlak'
    RECIPES.append((f'IC-{i + 1:03d}', concept, b, p, f))
    save_formulation(*RECIPES[-1])

trials = q("""SELECT t.*, pf.project_id, pf.concept_name FROM trials t
              LEFT JOIN parent_formulations pf ON pf.id = t.parent_formulation_id
              WHERE (t.is_deleted = 0 OR t.is_deleted IS NULL)""")
check('6 varyasyon kaydedildi', len(trials) == 6, f'{len(trials)} kayıt')
check('Varyasyonlar projeye bağlı', trials and all(t['project_id'] == PID for t in trials),
      str([t['project_id'] for t in trials]))
check('2 konsept oluştu', len({t['concept_name'] for t in trials}) == 2, str({t['concept_name'] for t in trials}))
if trials:
    comps = q("SELECT * FROM components WHERE trial_id = ?", (trials[0]['id'],))
    check('Bileşenler kaydedildi (5 satır)', len(comps) == 5, f'{len(comps)} satır')
    check('Bileşen adları/miktarları dolu', comps and all(c['component_name'] and (c['amount'] or 0) > 0 for c in comps),
          str([(c['component_name'], c['amount']) for c in comps][:2]))
    check('Varyasyon maliyeti kaydedildi', (trials[0]['total_cost'] or 0) > 0, str(trials[0]['total_cost']))
check('Kayıt başarı mesajı gösterildi', any(k == 'showinfo' for k, _ in DIALOGS), str(DIALOGS))
legacy = q("SELECT COUNT(*) n FROM formulations")[0]['n']
check('Eski (legacy) tabloya çift kayıt yok', legacy == 0, f'{legacy} satır')

app.sidebar.refresh()
all_tree = []
stack = list(app.sidebar.tree.get_children())
while stack:
    it = stack.pop()
    all_tree.append(app.sidebar.tree.item(it, 'text'))
    stack += list(app.sidebar.tree.get_children(it))
check('Varyasyonlar ağaçta görünüyor', sum('IC-' in s for s in all_tree) == 6, str(all_tree))
check('Editör listesinde varyasyonlar var', len(app.formulation_editor.formulation_list) >= 6,
      str(len(app.formulation_editor.formulation_list)))

# Aynı kodla tekrar kayıt → üzerine yaz (Evet)
ANSWERS['askyesnocancel'] = True
save_formulation('IC-001', 'İç Cephe Mat', 40, 20, 10)
n = q("SELECT COUNT(*) n FROM trials WHERE trial_code = 'IC-001' AND (is_deleted = 0 OR is_deleted IS NULL)")[0]['n']
check('Üzerine yazma yeni kayıt açmadı', n == 1, f'{n} kayıt')
t1 = q("SELECT id FROM trials WHERE trial_code = 'IC-001'")
if t1:
    comps = q("SELECT * FROM components WHERE trial_id = ?", (t1[0]['id'],))
    check('Üzerine yazmada bileşenler değişti', any(abs((c['amount'] or 0) - 40) < 0.01 for c in comps) and len(comps) == 5,
          str([(c['component_name'], c['amount']) for c in comps]))
# Hayır → revizyon
ANSWERS['askyesnocancel'] = False
save_formulation('IC-002', 'İç Cephe Mat', 30, 15, 10)
check('Revizyon oluşturuldu', len(q("SELECT id FROM trials WHERE trial_code = 'IC-002-REV1'")) == 1)
ANSWERS['askyesnocancel'] = True


# ---------------------------------------------------------------- 4. Test sonuçları
@step('Test sonucu kaydı')
def save_test(code, gloss, opacity, hardness):
    tp = app.test_results_panel
    tp._clear()
    tp.formulation_combo.set(code)
    tp._on_formulation_selected()
    values = {'gloss_60': gloss, 'opacity': opacity, 'hardness_konig': hardness, 'adhesion': 4}
    for group in tp.test_groups.values():
        for key, entry in group.entries.items():
            if key in values:
                entry.delete(0, tk.END)
                entry.insert(0, str(values[key]))
    DIALOGS.clear()
    tp._save()
    pump()


for code, concept, b, p, f in RECIPES:
    # Fiziksel olarak makul bir ilişki: bağlayıcı ↑ parlaklık ↑, pigment ↑ örtücülük ↑
    save_test(code, round(1.8 * b + random.uniform(-2, 2), 1), round(70 + 1.1 * p, 1), round(2 * b, 1))

tested = q("SELECT trial_code, gloss, opacity, hardness, quality_score FROM trials WHERE gloss IS NOT NULL")
check('Test sonuçları mevcut varyasyonlara yazıldı', len(tested) == 6, str(tested[:2]))
check('Test için yeni sahipsiz kayıt açılmadı',
      q("SELECT COUNT(*) n FROM trials WHERE parent_formulation_id IS NULL")[0]['n'] == 0)
check('Kalite skoru hesaplandı', tested and all(r['quality_score'] is not None for r in tested), str(tested[:2]))
check('Sertlik/opaklık eşlendi', tested and all(r['opacity'] and r['hardness'] for r in tested))

# Kayıtlı test sonucu geri yükleniyor mu
tp = app.test_results_panel
tp._clear()
tp.formulation_combo.set('IC-003')
tp._on_formulation_selected()
loaded = {}
for g in tp.test_groups.values():
    loaded.update(g.get_values())
check('Kayıtlı test sonucu forma geri yüklendi', 'gloss_60' in loaded, str(loaded))

# ---------------------------------------------------------------- 5. Arka plan ML
deadline = time.time() + 60
while time.time() < deadline:
    pump(0.5)
    if os.path.exists(os.path.join(WORK, 'assets', 'models', 'continuous_model.pkl')) and \
            not (app.learning_controller and app.learning_controller.is_training()):
        break
from src.ml_engine.continuous_learner import ContinuousLearner  # noqa: E402
learner = ContinuousLearner(os.path.join(WORK, 'assets', 'models'))
check('Arka plan eğitimi model üretti', 'gloss' in learner.models, str(list(learner.models)))
imp = learner.get_feature_importance().get('gloss', {}) if learner.models else {}
recipe_imp = sum(v for k, v in imp.items() if k not in ('viscosity', 'ph', 'density', 'coating_thickness'))
check('Model reçete özelliklerinden öğreniyor', recipe_imp > 0.5, f'reçete önem toplamı={recipe_imp:.2f}')

# ---------------------------------------------------------------- 6. Optimizasyon
res = app._on_generate_recipe({'gloss': 70})
check('Optimizasyon öneri üretti', res.get('success') and res.get('suggestions'), str(res.get('message')))
if res.get('suggestions'):
    preds = {round(s['prediction'].get('gloss', 0), 1) for s in res['suggestions']}
    check('Tahminler reçeteye göre değişiyor', len(preds) > 1 or abs(list(preds)[0] - 70) < 10, str(preds))
    app.optimization_panel._show_results(res)
    app._on_apply_optimization_recipe(res['suggestions'][0]['recipe'])
    pump()
    check('Öneri editöre aktarıldı', len(app.formulation_editor.grid.get_data()) == len(res['suggestions'][0]['recipe']))

# ---------------------------------------------------------------- 7. Ağaç navigasyonu
concept = q("SELECT id FROM parent_formulations WHERE concept_name = 'İç Cephe Mat'")
if concept:
    app.sidebar.tree.selection_set(f"c_{concept[0]['id']}")
    app.sidebar._on_select(None)
    pump()
    check('Konsept seçimi karşılaştırmayı açtı', app.notebook.index(app.notebook.select()) == 5)
    rows = app.comparison_panel.tree.get_children() if hasattr(app.comparison_panel, 'tree') else []
    check('Karşılaştırma tablosu doldu', len(rows) > 5, f'{len(rows)} satır')
    app.comparison_panel.load_concept(concept[0]['id'])
    tables = [w for w in app.comparison_panel.tree_frame.winfo_children() if w.winfo_class() == 'Treeview']
    check('Tekrar yükleme tabloyu çoğaltmadı', len(tables) == 1, f'{len(tables)} tablo')
tid = q("SELECT id FROM trials WHERE trial_code = 'IC-004'")[0]['id']
app.sidebar.tree.selection_set(f't_{tid}')
app.sidebar._on_select(None)
pump()
ed = app.formulation_editor
check('Varyasyon seçimi editörü doldurdu', ed.formula_code_entry.get() == 'IC-004' and len(ed.grid.get_data()) == 5,
      f"{ed.formula_code_entry.get()} / {len(ed.grid.get_data())} satır")

# Editördeki kayıtlı formül listesinden seçim
ed.formulation_combo.set(next(f['display'] for f in ed.formulation_list if f.get('formula_code') == 'IC-005'))
ed._on_formulation_selected()
pump()
check('Kayıtlı listeden seçim editörü doldurdu', ed.formula_code_entry.get() == 'IC-005')

# Sağ tık → yeni varyasyon (konsept altında)
if concept:
    app._on_sidebar_selection('new_trial_request', concept[0]['id'])
    pump()
    check('Yeni varyasyon isteği konsept adını doldurdu', ed.formula_name_entry.get() == 'İç Cephe Mat',
          repr(ed.formula_name_entry.get()))

# ---------------------------------------------------------------- 8. Dashboard
app._refresh_dashboard()
stats = db.get_dashboard_stats()
check('Dashboard toplam formül sayısı', stats.get('total_formulas') == 7, str(stats))
from app.components.dialogs import formulation_list_dialog as fld, trial_list_dialog as tld  # noqa: E402
opened = []
fld_orig, tld_orig = fld.FormulationListDialog.__init__, tld.TrialListDialog.__init__


def _spy(orig):
    def init(self, parent, title, items, *a, **k):
        opened.append((title, len(items)))
        orig(self, parent, title, items, *a, **k)
        self.destroy()
    return init


import app.ui_components as uic  # noqa: E402
uic.FormulationListDialog.__init__ = _spy(fld_orig)
uic.TrialListDialog.__init__ = _spy(tld_orig)
from src.core.translation_keys import TK  # noqa: E402
for card in (TK.DASHBOARD_STATS_TOTAL, TK.DASHBOARD_STATS_MONTHLY, TK.DASHBOARD_STATS_WAITING,
             TK.DASHBOARD_STATS_SUCCESS):
    app._on_dashboard_navigate(card)
    pump(0.1)
check('Dashboard kartı sayıyı gösteriyor',
      app.dashboard.stat_cards[TK.DASHBOARD_STATS_TOTAL].value_label.cget('text') == '7',
      app.dashboard.stat_cards[TK.DASHBOARD_STATS_TOTAL].value_label.cget('text'))
check('Ağaçta test sonucu simgesi var', any('✅' in s or '❌' in s for s in (
    app.sidebar.tree.item(i, 'text') for c in app.sidebar.tree.get_children(f'p_{PID}')
    for i in app.sidebar.tree.get_children(c))))
check('Dashboard içgörüleri gösteriliyor', len(app.dashboard.insight_content.winfo_children()) >= 2,
      str(len(app.dashboard.insight_content.winfo_children())))
check('Dashboard kartları liste açıyor', len(opened) == 4 and opened[0][1] == 7, str(opened))
check('Dashboard kartı hata vermedi', not app.status_bar.status_label.cget('text').startswith('Hata')
      if hasattr(app.status_bar, 'status_label') else True)

DIALOGS.clear()
app._generate_report()
report = DIALOGS[-1][1][1] if DIALOGS else ''
check('Rapor gerçek sayıları gösteriyor', 'Toplam Formül: 7' in report, report.strip()[:200])

# ---------------------------------------------------------------- 9. Silme
from app.components.dialogs.formulation_list_dialog import FormulationListDialog  # noqa: E402
all_f = db.get_all_formulations()
check('Tüm formülasyonlar listesi varyasyonları içeriyor', len(all_f) == 7, str(len(all_f)))
target = next((f for f in all_f if f.get('formula_code') == 'IC-006'), None)
if target:
    app._on_edit_formulation(target['id'])
    pump()
    check('Listeden düzenle editörü doldurdu', ed.formula_code_entry.get() == 'IC-006')
    app._on_delete_formulation(target['id'])
    pump()
    left = q("SELECT COUNT(*) n FROM trials WHERE trial_code = 'IC-006' AND (is_deleted = 0 OR is_deleted IS NULL)")[0]['n']
    check('Varyasyon silindi', left == 0)
    check('Silinen varyasyon ağaçtan kalktı', not app.sidebar.tree.exists(f"t_{target['id']}"))

# ---------------------------------------------------------------- 10. Dil
app._switch_language('en')
pump()
check('Dil İngilizceye geçti', 'Optimization' in app.notebook.tab(6, 'text'), app.notebook.tab(6, 'text'))
app._switch_language('tr')
pump()

# ---------------------------------------------------------------- Sonuç
pump(0.5)
check('Arayüz geri çağrılarında yakalanmamış hata yok', not CALLBACK_ERRORS, '\n'.join(CALLBACK_ERRORS)[:1500])
shot_dir = os.environ.get('HARNESS_SHOT_DIR')
if shot_dir:  # isteğe bağlı: sekmelerin ekran görüntüleri (ImageMagick 'import' gerekir)
    import subprocess
    root.geometry('1400x880+0+0')
    app.sidebar.tree.item(f'p_{PID}', open=True)
    for child in app.sidebar.tree.get_children(f'p_{PID}'):
        app.sidebar.tree.item(child, open=True)
    for idx, name in ((0, 'dashboard'), (3, 'test_results'), (5, 'comparison')):
        app.notebook.select(idx)
        if name == 'comparison' and concept:
            app.comparison_panel.load_concept(concept[0]['id'])
        pump(1.0)
        subprocess.run(['import', '-window', 'root', os.path.join(shot_dir, f'{name}.png')])

failed = [r for r in RESULTS if not r[1]]
print(f'\n{len(RESULTS) - len(failed)}/{len(RESULTS)} adım geçti')
root.destroy()
shutil.rmtree(WORK, ignore_errors=True)
sys.exit(1 if failed else 0)
