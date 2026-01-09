<div align="center">

# 🎨 Paint Formulation AI

### Intelligent Recipe Management for Chemical Engineering

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)]()

*Where Chemical Engineering meets Data Science*

</div>

---

## 📋 About

**Paint Formulation AI** is a desktop application designed for paint and coatings R&D engineers. It streamlines the formulation development process by combining traditional recipe management with machine learning-powered predictions.

Built with Python and Tkinter, this tool helps reduce development cycles by intelligently analyzing historical data to predict coating performance before physical testing.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📊 **Smart Excel Import** | Import formulations from Excel with on-the-fly material creation |
| 🧪 **Formulation Editor** | Excel-style grid with real-time cost & solid content calculations |
| 🤖 **ML Predictions** | XGBoost-powered predictions for quality, viscosity, and gloss |
| 💰 **Cost Analysis** | Automatic cost calculation based on material prices |
| 📁 **Project Management** | Hierarchical organization: Projects → Concepts → Trials |
| 📈 **Variation Comparison** | Side-by-side comparison of formulation variations |

---

## 🖼️ Screenshots

<div align="center">

| Main Dashboard | Formulation Editor |
|:--------------:|:------------------:|
| ![Dashboard](screenshots/dashboard.png) | ![Editor](screenshots/editor.png) |

| ML Predictions | Material Management |
|:--------------:|:-------------------:|
| ![ML Panel](screenshots/ml_panel.png) | ![Materials](screenshots/materials.png) |

</div>

> 📝 *Add screenshots to a `screenshots/` folder*

---

## 🚀 Installation

### Prerequisites
- Python 3.10 or higher
- Windows 10/11

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/paint-formulation-ai.git
cd paint-formulation-ai

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment (Windows)
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the application
python main.py
```

---

## 📦 Tech Stack

| Category | Technology |
|----------|------------|
| **Language** | Python 3.10+ |
| **GUI** | Tkinter / ttk |
| **Database** | SQLite |
| **Machine Learning** | XGBoost, Scikit-learn |
| **Data Processing** | Pandas, NumPy |
| **Excel Support** | openpyxl, xlsxwriter |

---

## 📁 Project Structure

```
paint-formulation-ai/
├── main.py                 # Application entry point
├── app/
│   ├── components/         # UI components
│   │   ├── editor/         # Formulation editor
│   │   ├── dialogs/        # Modal dialogs
│   │   └── ...
│   ├── views/              # Main views
│   └── ui_components.py    # Main application class
├── src/
│   ├── data_handlers/      # Database operations
│   └── ml_engine/          # Machine learning modules
├── assets/
│   └── models/             # Trained ML models
├── config.ini              # Configuration file
└── requirements.txt        # Dependencies
```

---

## 🛠️ Development

### Generate requirements.txt
```bash
pip freeze > requirements.txt
```

### Run in development mode
```bash
python main.py --debug
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Your Name**
- LinkedIn: www.linkedin.com/in/kadirayana
- Email: ayanakadir@hotmail.com

---

<div align="center">

Made with ❤️ for the Paint & Coatings Industry

</div>
