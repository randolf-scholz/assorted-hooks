r"""Test the check_unmaintained script."""

import tomllib
from contextlib import redirect_stdout
from io import BytesIO, StringIO

from assorted_hooks.check_requirements_maintained import check_pyproject

# NOTE: need bytes for `tomllib.load`.
TEST_PYPROJECT_TOML = rb"""
[project]
version = "0.1.0"
name = "assorted-hooks"

dependencies = ["wget>=3.2"]

[project.optional-dependencies]
test = ["unittest"]
"""

EXPECTED = """\
Direct dependency 'wget' appears unmaintained (latest release: 3.2 from 2015-10-22 15:26:37)
Optional dependency 'unittest' appears unmaintained (latest release: 0.0 from 2010-07-14 00:51:11)
"""


def test_check_simple_example():
    # fake input of pyproject.toml
    with BytesIO(TEST_PYPROJECT_TOML) as file:
        config = tomllib.load(file)

    # check the pyproject.toml
    with redirect_stdout(StringIO()) as stdout:
        assert check_pyproject(config) == 2

    assert stdout.getvalue() == EXPECTED


COMPLEX_EXAMPLE = rb"""
[project]
requires-python = ">=3.11,<3.13"
name = "example"
version = "0.10"

dependencies = [
    # nvidia = [
    # "nvidia-cublas-cu11>=11.11.3",
    # "nvidia-cublas-cu12>=12.1.3.1",
    # "nvidia-cuda-nvrtc-cu11>=11.8.89",
    # "nvidia-cuda-runtime-cu11>=11.8.89",
    # "nvidia-cuda-runtime-cu12>=12.1.105",
    # "nvidia-cudnn-cu11>=8.9.4",
    # "nvidia-cudnn-cu12>=8.9.2.26",
    # "nvidia-ml-py>=12.550.52",
    # devtools = [
    "johnnydep>=1.20.4",
    "ninja>=1.11.1.1",
    "pip-tools>=7.4.1",
    "pipdeptree>=2.23.0",
    "pre-commit>=3.7.1",
    "pybadges>=3.0.1",
    "pydeps>=1.12.20",
    "setuptools>=70.1.1",
    "twine>=5.1.1",
    "wheel>=0.43.0",
    # linters = [
    "bandit>=1.7.9",
    "mccabe>=0.7.0",
    "pycodestyle>=2.12.0",
    "pydocstyle>=6.3.0",
    "pyflakes>=3.2.0",
    "pylint>=3.2.5",
    "ruff>=0.5.0",
    "ruff-lsp>=0.0.54",
    "slotscheck>=0.19.0",
    # formatters = [
    "black[jupyter]>=24.4.2",
    "blacken-docs>=1.18.0",
    "isort>=5.13.2",
    "nbqa>=1.8.5",
    "pyment>=0.3.3",
    "pyall>=0.3.5",
    "ssort>=0.13.0",
    # typecheckers = [
    "mypy>=1.10.1",
    "pyre-check>=0.9.22",
    "pyright>=1.1.369",
    "typeguard>=4.3.0",
    # scipy-stack = [
    "numpy>=1.26.4",
    "ipython>=8.26.0",
    "scipy>=1.14.0",
    "matplotlib>=3.9.0",
    "pandas>=2.2.2",
    "sympy>=1.12.1",
    "nose2>=0.15.1",
    # numfocus = [
    "aesara>=2.9.3",
    "arviz>=0.18.0",
    "bokeh>=3.4.2",
    "cupy-cuda12x>=13.2.0",
    "dask>=2024.6.2",
    "networkx>=3.3",
    # "nteract-on-jupyter >=2.1.3",
    "scikit-bio>=0.6.1",
    "scikit-image>=0.24.0",
    "scikit-learn>=1.5.0",
    "statsmodels>=0.14.2",
    "tables>=3.9.2",
    "xarray>=2024.6.0",
    "zarr>=2.18.2",
    # testing = [
    "pytest>=8.2.2",
    "pytest-benchmark>=4.0.0",
    "pytest-cov>=5.0.0",
    "pytest-rerunfailures>=14.0",
    "pytest-xdist>=3.6.1",
    # jupyter = [
    "ipydex>=0.16.2",
    "ipympl>=0.9.4",
    "ipython-autotime>=0.3.2",
    "ipywidgets>=8.1.3",
    "jupyter-client>=8.6.2",
    "jupyter-core>=5.7.2",
    "jupyter-packaging>=0.12.3",
    "jupyter-resource-usage>=1.0.2",
    "jupyterlab>=4.2.3",
    "jupyterlab-code-formatter>=2.2.1",
    # "jupyterlab-drawio >=0.9.0",
    "jupyterlab-execute-time>=3.1.2",
    "jupyterlab-git>=0.50.1",
    "jupyterlab-lsp>=5.1.0",
    "jupyterlab-mathjax3>=4.3.0",
    "jupyterlab-spellchecker>=0.8.4",
    # "jupyterlab-spreadsheet-editor >=0.6.1",
    "jupyterlab-templates>=0.5.2",
    # "jupyterlab-tensorboard-pro  >=0.7.0",
    "jupyterlab-widgets>=3.0.11",
    "jupytext>=1.16.2",
    "nbconvert>=7.16.4",
    "nbdime>=4.0.1",
    "nbformat>=5.10.4",
    "nbstripout>=0.7.1",
    "rise>=5.7.1",
    # "voila >=0.2.12",
    # torch = [
    #"fastai>=2.7.15",
    "pytorch-ignite>=0.5.0",
    "pytorch-lightning>=2.3.1",
    "torch>=2.3.1",
    "torch-tb-profiler>=0.4.3",
    "torchaudio>=2.3.1",
    "torchdata>=0.7.1",
    "torchdiffeq>=0.2.4",
    "torchinfo>=1.8.0",
    "torchmetrics>=1.4.0",
    "torchtext>=0.18.0",
    "torchvision>=0.18.1",
    # types = [
    "pandas-stubs>=2.2.2.240603",
    "types-chardet>=5.0.4.6",
    "types-cryptography>=3.3.23.2",
    "types-docutils>=0.21.0.20240423",
    "types-filelock>=3.2.7",
    "types-pillow>=10.2.0.20240520",
    "types-protobuf>=5.27.0.20240626",
    "types-pyopenssl>=24.1.0.20240425",
    "types-python-dateutil>=2.9.0.20240316",
    "types-pytz>=2024.1.0.20240417",
    "types-pyyaml>=6.0.12.20240311",
    "types-redis>=4.6.0.20240425",
    "types-requests>=2.32.0.20240622",
    "types-setuptools>=70.1.0.20240627",
    "types-tabulate>=0.9.0.20240106",
    # sphinx = [
    "docutils>=0.21.2",
    "karma-sphinx-theme>=0.0.8",
    "nbsphinx>=0.9.4",
    "numpydoc>=1.7.0",
    "piccolo-theme>=0.23.0",
    "pydata-sphinx-theme>=0.15.4",
    "sphinx>=7.3.7",
    "sphinx-autoapi>=3.1.2",
    "sphinx-autodoc-typehints>=2.2.2",
    "sphinx-copybutton>=0.5.2",
    "sphinx-math-dollar>=1.2.1",
    "sphinx-pdj-theme>=0.4.0",
    "sphinx-typo3-theme>=4.9.0",
    # jax = [
    "chex>=0.1.86",
    "dm-control>=1.0.20",
    "dm-env>=1.6",
    "dm-haiku>=0.0.12",
    "dm-pix>=0.4.2",
    "dm-sonnet>=2.0.2",
    "dm-tree>=0.1.8",
    "equinox>=0.11.4",
    "flax>=0.8.5",
    "jax[cuda12]>=0.4.28",
    "jaxlib>=0.4.28",
    "jmp>=0.0.4",
    "objax>=1.8.0",
    "optax>=0.2.2",
    "rlax>=0.1.6",
    # tensorflow = [
    "keras>=3.4.1",
    "tensorflow>=2.16.2",
    "tensorflow-datasets>=4.9.6",
    "tensorflow-estimator>=2.15.0",
    "tensorflow-metadata>=1.15.0",
    "tensorflow-probability>=0.24.0",
    # "tensorflow-text>=2.16.1",        # does not support 3.12
    # tensorboard = [
    "tensorboard>=2.16.2",
    "tbparse>=0.0.8",
    # other = [
    # "aim>=4.1.0",
    #    "apache-airflow>=2.8.1",
    "click>=8.1.7",
    "cmake>=3.29.6",
    "darts>=0.30.0",
    "cvxopt>=1.3.2",
    "dill>=0.3.8",
    "einops>=0.8.0",
    "fastparquet>=2024.5.0",
    "gitpython>=3.1.43",
    "graphviz>=0.20.3",
    "gym>=0.26.2",
    "h5py>=3.11.0",
    "hyperopt>=0.2.7",
    "kaggle>=1.6.14",
    "mpmath>=1.3.0",
    "mujoco>=3.1.6",
    "multidict>=6.0.5",
    "numba>=0.60.0",
    "opencv-python>=4.10.0.84",
    "opencv-python-headless>=4.10.0.84",
    "openml>=0.14.2",
    "openpyxl>=3.1.5",
    "opt-einsum>=3.3.0",
    "optuna>=3.6.1",
    "pillow>=10.3.0",
    "plotly>=5.22.0",
    "polars[numpy,pandas,pyarrow]>=0.20.31",
    "protobuf>=4.25.3",
    "pyarrow>=16.1.0",
    "pydantic>=2.7.4",
    "pygithub>=2.3.0",
    "pytz>=2024.1",
    "pymysql>=1.1.1",
    "pyyaml>=6.0.1",
    "ray[default,tune]>=2.31.0",
    "requests>=2.32.3",
    "sacrebleu>=2.4.2",
    "seaborn>=0.13.2",
    "sktime>=0.30.1",
    "sortedcontainers>=2.4.0",
    "sqlalchemy>=2.0.31",
    "termcolor>=2.4.0",
    "tqdm>=4.66.4",
    "tsai>=0.2.17",
    "urllib3>=2.2.2",
    "vispy>=0.14.3",
]

[tool.poetry.dependencies]
python = ">=3.11, <3.13"
pip = ">=24.1.1"

[tool.poetry.group.scipy-stack.dependencies]
numpy = ">=1.26.4"
ipython = ">=8.26.0"
scipy = ">=1.14.0"
matplotlib = ">=3.9.0"
pandas = ">=2.2.2"
sympy = ">=1.12.1"
nose2 = ">=0.15.1"

[tool.poetry.group.numfocus.dependencies]
aesara = ">=2.9.3"
arviz = ">=0.18.0"
bokeh = ">=3.4.2"
cupy-cuda12x = ">=13.2.0"
dask = ">=2024.6.2"
networkx = ">=3.3"
scikit-bio = ">=0.6.1"
scikit-image = ">=0.24.0"
scikit-learn = ">=1.5.0"
statsmodels = ">=0.14.2"
tables = ">=3.9.2"
xarray = ">=2024.6.0"
zarr = ">=2.18.2"

[tool.poetry.group.test.dependencies]
coverage = ">=7.5.4"
pytest = ">=8.2.2"
pytest-benchmark = ">=4.0.0"
pytest-cov = ">=5.0.0"
pytest-rerunfailures = ">=14.0"
pytest-xdist = ">=3.6.1"

[tool.poetry.group.docs.dependencies]
docutils = ">=0.21.2"
myst_parser = ">=3.0.1"
nbsphinx = ">=0.9.4"
numpydoc = ">=1.7.0"
pandoc = ">=2.3"
piccolo-theme = ">=0.23.0"
pydata-sphinx-theme = ">=0.15.4"
sphinx = ">=7.3.7"
sphinx-autoapi = ">=3.1.2"
sphinx-autodoc-typehints = ">=2.2.2"
sphinx-automodapi = ">=0.17.0"
sphinx-copybutton = ">=0.5.2"
sphinx-math-dollar = ">=1.2.1"
sphinx-pdj-theme = ">=0.4.0"
sphinx-typo3-theme = ">=4.9.0"

[tool.poetry.group.devtools.dependencies]
cmake = ">=3.29.6"
devtools = ">=0.12.2"
johnnydep = ">=1.20.4"
ninja = ">=1.11.1.1"
pip = ">=24.1.1"
pip-tools = ">=7.4.1"
pipdeptree = ">=2.23.0"
pre-commit = ">=3.7.1"
pybadges = ">=3.0.1"
pydeps = ">=1.12.20"
setuptools = ">=70.1.1"
twine = ">=5.1.1"
wheel = ">=0.43.0"

[tool.poetry.group.formatters.dependencies]
black = { version = ">=24.4.2", extras = ["d", "jupyter"] }
blacken-docs = ">=1.18.0"
isort = ">=5.13.2"
nbstripout-fast = ">=1.0.4"
nbqa = ">=1.8.5"
ssort = ">=0.13.0"

[tool.poetry.group.linters.dependencies]
pycodestyle = ">=2.12.0"
pydocstyle = ">=6.3.0"
pyflakes = ">=3.2.0"
pylint = ">=3.2.5"
ruff = ">= 0.5.0"
ruff-lsp = ">= 0.0.54"
slotscheck = ">=0.19.0"

[tool.poetry.group.jax.dependencies]
chex = ">=0.1.86"
dm-control = ">=1.0.20"
dm-env = ">=1.6"
dm-haiku = ">=0.0.12"
dm-pix = ">=0.4.2"
dm-sonnet = ">=2.0.2"
dm-tree = ">=0.1.8"
equinox = ">=0.11.4"
flax = ">=0.8.5"
jax = { version = ">=0.4.28", extras = ["cuda12"] }
jaxlib = { version = ">=0.4.28" }
jmp = ">=0.0.4"
objax = ">=1.8.0"
optax = ">=0.2.2"
rlax = ">=0.1.6"

[tool.poetry.group.jupyter.dependencies]
ipydex = ">=0.16.2"
ipympl = ">=0.9.4"
ipython-autotime = ">=0.3.2"
ipywidgets = ">=8.1.3"
jupyter-client = ">=8.6.2"
jupyter-core = ">=5.7.2"
jupyter-packaging = ">=0.12.3"
jupyter-resource-usage = ">=1.0.2"
jupyterlab = ">=4.2.3"
jupyterlab-code-formatter = ">=2.2.1"
# jupyterlab-drawio = ">=0.9.0"
jupyterlab-execute-time = ">=3.1.2"
jupyterlab-git = ">=0.50.1"
jupyterlab-lsp = ">=5.1.0"
jupyterlab-mathjax3 = ">=4.3.0"
jupyterlab-spellchecker = ">=0.8.4"
# jupyterlab-spreadsheet-editor = ">=0.6.1"
jupyterlab-templates = ">= 0.5.2"
# jupyterlab-skip-traceback = ">=5.0.0"
# jupyterlab-tensorboard-pro = ">=0.7.0"
jupyterlab_widgets = ">=3.0.11"
jupytext = ">=1.16.2"
nbconvert = ">=7.16.4"
nbdime = ">=4.0.1"
nbstripout = ">=0.7.1"
notebook = ">=7.2.1"
python-lsp-server = ">=1.11.0"
rise = ">=5.7.1"
# voila = ">=0.4.0"

[tool.poetry.group.tensorflow.dependencies]
keras = ">=3.4.1"
tensorflow = ">=2.16.2"
tensorflow-datasets = ">=4.9.6"
tensorflow-estimator = ">=2.15.0"
tensorflow-metadata = ">=1.15.0"
tensorflow-probability = ">=0.24.0"
# tensorflow-text = ">=2.16.1"  # does not support 3.12

[tool.poetry.group.tensorboard.dependencies]
tensorboard = ">=2.16.2"
tbparse = ">=0.0.8"

[tool.poetry.group.torch.dependencies]
# fastai = ">=2.7.15"
pytorch-ignite = ">=0.5.0"
pytorch-lightning = ">=2.3.1"
torch = ">=2.3.1"
torch-tb-profiler = ">=0.4.3"
torchaudio = ">=2.3.1"
torchdata = ">=0.7.1"
torchdiffeq = ">=0.2.4"
torchinfo = ">=1.8.0"
torchmetrics = ">=1.4.0"
torchtext = ">=0.18.0"
torchvision = ">=0.18.1"

[tool.poetry.group.typing.dependencies]
mypy = ">=1.10.1"
pyright = ">=1.1.369"
pyre-check = ">=0.9.22"
typeguard = ">=4.3.0"
types-chardet = ">=5.0.4.6"
types-colorama = ">=0.4.15.20240311"
types-cryptography = ">=3.3.23.2"
types-decorator = ">=5.1.8.20240310"
types-docutils = ">=0.21.0.20240423"
types-filelock = ">=3.2.7"
types-pillow = ">=10.2.0.20240520"
types-protobuf = ">=5.27.0.20240626"
types-psutil = ">=6.0.0.20240621"
types-pygments = ">=2.18.0.20240506"
types-pyopenssl = ">=24.1.0.20240425"
types-python-dateutil = ">=2.9.0.20240316"
types-pytz = ">=2024.1.0.20240417"
types-pyyaml = ">=6.0.12.20240311"
types-redis = ">=4.6.0.20240425"
types-requests = ">=2.32.0.20240622"
types-setuptools = ">=70.1.0.20240627"
types-tabulate = ">=0.9.0.20240106"
types-tqdm = ">=4.66.0.20240417"
types-urllib3 = ">=1.26.25.14"
typing-extensions = ">=4.12.2"

[tool.poetry.group.timeseries.dependencies]
darts = ">=0.30.0"        # A python library for easy manipulation and forecasting of time series.
statsforecast = ">=1.7.5" # Time series forecasting suite using statistical models
# tsai = ">=0.2.17"       # Practical Deep Learning for Time Series / Sequential Data library based on fastai v2/Pytorch
# sktime = ">=0.30.1"     # A unified framework for machine learning with time series
# pytorch-forecasting = ">=1.0.0"  # Time series forecasting with PyTorch

[tool.poetry.group.hyperparameter.dependencies]
optuna = ">=3.6.1"

[tool.poetry.group.unsorted.dependencies]
# aim = {version=">=4.1.0", allow-prereleases=true}
# apache-airflow = ">=2.8.1"
# ivy = ">=0.0.3.0"
click = ">=8.1.7"
cvxopt = ">=1.3.2"
dill = ">=0.3.8"
einops = ">=0.8.0"
fastparquet = ">=2024.5.0"
gitpython = ">=3.1.43"
graphviz = ">=0.20.3"
gym = ">=0.26.2"
h5py = ">=3.11.0"
hyperopt = ">=0.2.7"
kaggle = ">=1.6.14"
mpmath = ">=1.3.0"
mujoco = ">=3.1.6"
multidict = ">=6.0.5"
numba = ">=0.60.0"
opencv-python = ">=4.10.0.84"
opencv-python-headless = ">=4.10.0.84"
openml = ">=0.14.2"
openpyxl = ">=3.1.5"
opt-einsum = ">=3.3.0"
pillow = ">=10.3.0"
plotly = ">=5.22.0"
polars = { version = ">=0.20.31", extras = ["numpy", "pandas", "pyarrow"] }
protobuf = ">=4.25.3"
pyarrow = ">=16.1.0"
pydantic = ">=2.7.4"
pygithub = ">=2.3.0"
pygments = ">=2.18.0"
pymysql = ">=1.1.1"
pytz = ">=2024.1"
pyyaml = ">=6.0.1"
ray = { version = ">=2.31.0", extras = ["default", "tune"] }
requests = ">=2.32.3"
sacrebleu = ">=2.4.2"
seaborn = ">=0.13.2"
sortedcontainers = ">=2.4.0"
sqlalchemy = ">=2.0.31"
termcolor = ">=2.4.0"
tqdm = ">=4.66.4"
urllib3 = ">=2.2.2"
vispy = ">=0.14.3"
wandb = ">=0.17.3"
wget = ">=3.2"
# endregion poetry configuration -------------------------------------------------------
"""


def test_check_complex_example():
    # fake input of pyproject.toml
    with BytesIO(COMPLEX_EXAMPLE) as file:
        config = tomllib.load(file)

    # check the pyproject.toml
    with redirect_stdout(StringIO()) as stdout:
        assert check_pyproject(config) > 1

    print(stdout.getvalue())
