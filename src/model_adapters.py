"""Actual framework adapters for the five project comparison models.

The caller owns chronological splitting and train-only preprocessing. All X
arrays must already be finite float features on the same scale; y is a daily
return in percentage points. No test targets are accepted by this module.

API references used while implementing this module:
https://keras.io/api/callbacks/early_stopping/
https://keras.io/guides/migrating_to_keras_3/
https://docs.fast.ai/tabular.learner.html
https://docs.fast.ai/callback.tracker.html
https://github.com/dreamquark-ai/tabnet
https://lightning-flash.readthedocs.io/en/stable/api/generated/flash.core.model.Task.html
"""

from __future__ import annotations

import copy
import importlib.metadata
import json
import os
from pathlib import Path
import random
import time
from typing import Any

import numpy as np


def _versions(*packages: str) -> dict[str, str]:
    result = {}
    for package in packages:
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result[package] = "not installed"
    return result


def _seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    os.environ.setdefault("KERAS_BACKEND", "torch")
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    import torch

    torch.set_num_threads(2)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def _arrays(Xtrain, ytrain, Xval, yval, Xtest):
    xt, xv, xs = [np.asarray(x, dtype=np.float32) for x in (Xtrain, Xval, Xtest)]
    yt, yv = [np.asarray(y, dtype=np.float32).reshape(-1) for y in (ytrain, yval)]
    if any(x.ndim != 2 for x in (xt, xv, xs)):
        raise ValueError("Feature arrays must be two-dimensional.")
    if len(xt) != len(yt) or len(xv) != len(yv):
        raise ValueError("Feature and target row counts differ.")
    if not (xt.shape[1] == xv.shape[1] == xs.shape[1]):
        raise ValueError("Feature counts differ between splits.")
    if not all(np.isfinite(x).all() for x in (xt, xv, xs, yt, yv)):
        raise ValueError("Adapters require finite inputs; preprocess on training data first.")
    return xt, yt, xv, yv, xs


def fit_predict(
    name: str,
    Xtrain,
    ytrain,
    Xval,
    yval,
    Xtest,
    seed: int = 42,
    output_dir: str | Path = "models",
    config: dict[str, Any] | None = None,
):
    """Train one named framework and return (validation, test, metadata).

    Validation is used for stopping. Test features are only passed to prediction
    after fitting has finished. Supported names: xgboost, keras, fastai, tabnet,
    flash. Common config keys: max_epochs, patience, batch_size, learning_rate.
    XGBoost-specific config keys are passed as estimator hyperparameters.
    """
    name = name.lower()
    if name not in {"xgboost", "keras", "fastai", "tabnet", "flash"}:
        raise ValueError(f"Unknown model: {name}")
    _seed(seed)
    arrays = _arrays(Xtrain, ytrain, Xval, yval, Xtest)
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    cfg = dict(config or {})
    start = time.perf_counter()
    fn = globals()[f"_fit_{name}"]
    val, test, meta = fn(*arrays, seed=seed, folder=folder, cfg=cfg)
    val = np.asarray(val, dtype=float).reshape(-1)
    test = np.asarray(test, dtype=float).reshape(-1)
    if len(val) != len(arrays[2]) or len(test) != len(arrays[4]):
        raise RuntimeError(f"{name}: prediction lengths do not match the split.")
    if not np.isfinite(val).all() or not np.isfinite(test).all():
        raise RuntimeError(f"{name}: predictions contain nonfinite values.")
    meta.update(
        name=name,
        seed=seed,
        n_features=arrays[0].shape[1],
        n_train=len(arrays[0]),
        n_validation=len(arrays[2]),
        target_unit="percentage points",
        elapsed_seconds=round(time.perf_counter() - start, 3),
        validation_mse=float(np.mean((arrays[3] - val) ** 2)),
        test_used_for_training=False,
    )
    (folder / f"{name}_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return val, test, meta


def _fit_xgboost(xt, yt, xv, yv, xs, *, seed, folder, cfg):
    from xgboost import XGBRegressor

    params = dict(
        objective="reg:squarederror",
        n_estimators=400,
        max_depth=3,
        learning_rate=0.03,
        min_child_weight=5,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=5.0,
        tree_method="hist",
        n_jobs=2,
        random_state=seed,
        early_stopping_rounds=20,
        eval_metric="rmse",
    )
    params.update(cfg)
    model = XGBRegressor(**params)
    model.fit(xt, yt, eval_set=[(xv, yv)], verbose=False)
    artifact = folder / "xgboost.ubj"
    model.save_model(artifact)
    history = model.evals_result()
    return model.predict(xv), model.predict(xs), dict(
        framework="XGBoost",
        versions=_versions("xgboost"),
        model_path=str(artifact),
        hyperparameters=params,
        epochs_run=len(history["validation_0"]["rmse"]),
        best_epoch=int(model.best_iteration) + 1,
        history=history,
    )


def _fit_keras(xt, yt, xv, yv, xs, *, seed, folder, cfg):
    # Set before importing keras: this project intentionally uses its torch backend.
    os.environ["KERAS_BACKEND"] = "torch"
    import keras

    keras.backend.clear_session()
    keras.utils.set_random_seed(seed)
    max_epochs = int(cfg.get("max_epochs", 40))
    patience = int(cfg.get("patience", 5))
    batch_size = int(cfg.get("batch_size", 64))
    lr = float(cfg.get("learning_rate", 0.001))
    model = keras.Sequential(
        [
            keras.layers.Input((xt.shape[1],)),
            keras.layers.Dense(64, activation="relu", kernel_regularizer=keras.regularizers.L2(0.001)),
            keras.layers.Dropout(0.1),
            keras.layers.Dense(32, activation="relu", kernel_regularizer=keras.regularizers.L2(0.001)),
            keras.layers.Dense(1),
        ]
    )
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=lr), loss="mse")
    history = model.fit(
        xt,
        yt,
        validation_data=(xv, yv),
        epochs=max_epochs,
        batch_size=batch_size,
        shuffle=True,
        verbose=0,
        callbacks=[
            keras.callbacks.EarlyStopping(monitor="val_loss", mode="min", patience=patience, restore_best_weights=True),
            keras.callbacks.TerminateOnNaN(),
        ],
    )
    artifact = folder / "keras.keras"
    model.save(artifact)
    hist = {key: [float(x) for x in values] for key, values in history.history.items()}
    return model.predict(xv, verbose=0), model.predict(xs, verbose=0), dict(
        framework="Keras 3 with PyTorch backend",
        versions=_versions("keras", "torch"),
        model_path=str(artifact),
        hyperparameters=dict(hidden_layers=[64, 32], activation="relu", dropout=0.1, l2=0.001,
                             max_epochs=max_epochs, patience=patience, batch_size=batch_size,
                             learning_rate=lr, optimizer="Adam", loss="mse"),
        epochs_run=len(hist["loss"]),
        best_epoch=int(np.argmin(hist["val_loss"])) + 1,
        history=hist,
    )


def _fit_fastai(xt, yt, xv, yv, xs, *, seed, folder, cfg):
    import pandas as pd
    import torch
    from fastai.callback.core import Callback
    from fastai.callback.tracker import EarlyStoppingCallback
    from fastai.tabular.all import RegressionBlock, TabularPandas, tabular_config, tabular_learner

    class KeepBestInMemory(Callback):
        """Avoid pickle-loading during stopping; restore exact best state tensors."""

        order = 59

        def before_fit(self):
            self.best_loss = float("inf")
            self.best_epoch = 0
            self.best_state = None

        def after_epoch(self):
            value = float(self.recorder.values[-1][1])
            if value < self.best_loss:
                self.best_loss = value
                self.best_epoch = int(self.epoch) + 1
                self.best_state = copy.deepcopy(self.model.state_dict())

        def after_fit(self):
            if self.best_state is None:
                raise RuntimeError("fastai did not produce a valid checkpoint.")
            self.model.load_state_dict(self.best_state)

    max_epochs = int(cfg.get("max_epochs", 40))
    patience = int(cfg.get("patience", 5))
    batch_size = int(cfg.get("batch_size", 64))
    lr = float(cfg.get("learning_rate", 0.001))
    columns = [f"feature_{i}" for i in range(xt.shape[1])]
    df = pd.DataFrame(np.concatenate([xt, xv]), columns=columns)
    df["target"] = np.concatenate([yt, yv])
    splits = (list(range(len(xt))), list(range(len(xt), len(df))))
    # Scaling was already fitted on the training block by the caller.
    tab = TabularPandas(df, procs=[], cat_names=[], cont_names=columns,
                        y_names="target", y_block=RegressionBlock(), splits=splits)
    dls = tab.dataloaders(bs=batch_size, num_workers=0, device=torch.device("cpu"))
    best = KeepBestInMemory()
    model_config = tabular_config(ps=[0.1, 0.0], use_bn=False, bn_cont=False)
    learner = tabular_learner(dls, layers=[64, 32], config=model_config,
                              loss_func=torch.nn.MSELoss(), wd=0.001,
                              cbs=[best, EarlyStoppingCallback(monitor="valid_loss", patience=patience)])
    with learner.no_bar(), learner.no_logging():
        learner.fit(max_epochs, lr=lr)
    learner.model.eval()

    def pred(x):
        with torch.no_grad():
            cats = torch.empty((len(x), 0), dtype=torch.long)
            return learner.model(cats, torch.from_numpy(x)).numpy().reshape(-1)

    artifact = folder / "fastai.pth"
    torch.save(learner.model.state_dict(), artifact)
    hist = [[float(x) for x in row] for row in learner.recorder.values]
    return pred(xv), pred(xs), dict(
        framework="fastai TabularPandas + tabular_learner",
        versions=_versions("fastai", "torch"),
        model_path=str(artifact),
        hyperparameters=dict(hidden_layers=[64, 32], activation="relu", dropout=[0.1, 0.0],
                             use_bn=False, bn_cont=False, weight_decay=0.001,
                             max_epochs=max_epochs, patience=patience, batch_size=batch_size,
                             learning_rate=lr, optimizer="fastai Adam", loss="mse"),
        epochs_run=len(hist),
        best_epoch=best.best_epoch,
        history={"train_loss": [r[0] for r in hist], "val_loss": [r[1] for r in hist]},
    )


def _fit_tabnet(xt, yt, xv, yv, xs, *, seed, folder, cfg):
    import torch
    from pytorch_tabnet.tab_model import TabNetRegressor

    max_epochs = int(cfg.get("max_epochs", 40))
    patience = int(cfg.get("patience", 5))
    batch_size = int(cfg.get("batch_size", 256))
    lr = float(cfg.get("learning_rate", 0.01))
    model = TabNetRegressor(
        n_d=8, n_a=8, n_steps=3, gamma=1.3,
        optimizer_fn=torch.optim.Adam,
        optimizer_params={"lr": lr},
        lambda_sparse=0.001,
        seed=seed, verbose=0, device_name="cpu",
    )
    model.fit(
        xt, yt.reshape(-1, 1),
        eval_set=[(xv, yv.reshape(-1, 1))], eval_name=["validation"],
        eval_metric=["mse"], max_epochs=max_epochs, patience=patience,
        batch_size=batch_size, virtual_batch_size=min(64, batch_size),
        num_workers=0, drop_last=False,
    )
    artifact = model.save_model(str(folder / "tabnet"))
    history = {key: [float(x) for x in value] for key, value in model.history.history.items()}
    return model.predict(xv), model.predict(xs), dict(
        framework="pytorch-tabnet TabNetRegressor",
        versions=_versions("pytorch-tabnet", "torch"),
        model_path=str(artifact),
        hyperparameters=dict(n_d=8, n_a=8, n_steps=3, gamma=1.3, lambda_sparse=0.001,
                             max_epochs=max_epochs, patience=patience, batch_size=batch_size,
                             virtual_batch_size=min(64, batch_size), learning_rate=lr, optimizer="Adam", loss="mse"),
        epochs_run=len(history["loss"]),
        best_epoch=int(model.best_epoch) + 1,
        history=history,
        feature_importances=[float(x) for x in model.feature_importances_],
    )


def _dense_torch_model(n_features):
    import torch

    return torch.nn.Sequential(
        torch.nn.Linear(n_features, 64), torch.nn.ReLU(), torch.nn.Dropout(0.1),
        torch.nn.Linear(64, 32), torch.nn.ReLU(), torch.nn.Linear(32, 1),
    )


def _fit_flash(xt, yt, xv, yv, xs, *, seed, folder, cfg):
    # PL 1.9's checkpoint callback uses this deprecated spelling. Keep the
    # compatibility bridge local to the legacy Flash path when NumPy >=2 is used.
    if "Inf" not in np.__dict__:
        np.Inf = np.inf
    import torch
    import flash
    from flash.core.model import Task
    from pytorch_lightning.callbacks import Callback, EarlyStopping, ModelCheckpoint
    from torch.utils.data import DataLoader, TensorDataset

    max_epochs = int(cfg.get("max_epochs", 40))
    patience = int(cfg.get("patience", 5))
    batch_size = int(cfg.get("batch_size", 64))
    lr = float(cfg.get("learning_rate", 0.001))

    class ReturnRegressionTask(Task):
        """A real Flash Task with a numeric dense regression backbone."""

        def __init__(self):
            super().__init__(model=_dense_torch_model(xt.shape[1]), loss_fn=torch.nn.MSELoss(),
                             optimizer="Adam", learning_rate=lr)

        def training_step(self, batch, batch_idx):
            x, y = batch
            # Flash normalizes its loss_fn argument to a name->callable mapping.
            loss = torch.nn.functional.mse_loss(self(x), y)
            self.log("train_loss", loss, on_step=False, on_epoch=True, batch_size=len(x))
            return loss

        def validation_step(self, batch, batch_idx):
            x, y = batch
            loss = torch.nn.functional.mse_loss(self(x), y)
            self.log("val_loss", loss, on_step=False, on_epoch=True, batch_size=len(x))
            return loss

        def configure_optimizers(self):
            return torch.optim.Adam(self.parameters(), lr=lr, weight_decay=0.001)

    class History(Callback):
        def __init__(self):
            self.rows = []

        def on_validation_epoch_end(self, trainer, pl_module):
            if not trainer.sanity_checking:
                value = trainer.callback_metrics.get("val_loss")
                if value is not None:
                    self.rows.append({"epoch": int(trainer.current_epoch) + 1,
                                      "val_loss": float(value)})

    def loader(x, y, shuffle):
        gen = torch.Generator().manual_seed(seed)
        return DataLoader(TensorDataset(torch.from_numpy(x), torch.from_numpy(y.reshape(-1, 1))),
                          batch_size=batch_size, shuffle=shuffle, num_workers=0, generator=gen)

    task = ReturnRegressionTask()
    history = History()
    checkpoint = ModelCheckpoint(dirpath=str(folder / "flash_checkpoints"), filename="best",
                                 monitor="val_loss", mode="min", save_top_k=1, save_weights_only=True)
    trainer = flash.Trainer(
        max_epochs=max_epochs, accelerator="cpu", devices=1, logger=False,
        callbacks=[history, checkpoint, EarlyStopping(monitor="val_loss", mode="min", patience=patience)],
        enable_progress_bar=False, enable_model_summary=False, deterministic=True,
        num_sanity_val_steps=0, default_root_dir=str(folder),
    )
    trainer.fit(task, train_dataloader=loader(xt, yt, True), val_dataloaders=loader(xv, yv, False))
    if not checkpoint.best_model_path:
        raise RuntimeError("Flash produced no best checkpoint.")
    state = torch.load(checkpoint.best_model_path, map_location="cpu", weights_only=False)
    task.load_state_dict(state["state_dict"])
    task.eval()

    def pred(x):
        with torch.no_grad():
            return task(torch.from_numpy(x)).numpy().reshape(-1)

    artifact = folder / "flash.pth"
    torch.save(task.model.state_dict(), artifact)
    return pred(xv), pred(xs), dict(
        framework="Lightning Flash 0.8.2 core Task, custom dense regression backbone",
        implementation_note="Real flash.core.model.Task subclass trained by flash.Trainer; not Flash's optional tabular-classification backbone.",
        versions=_versions("lightning-flash", "pytorch-lightning", "torchmetrics", "torch"),
        model_path=str(artifact),
        checkpoint_path=str(checkpoint.best_model_path),
        hyperparameters=dict(hidden_layers=[64, 32], activation="relu", dropout=0.1, weight_decay=0.001,
                             max_epochs=max_epochs, patience=patience, batch_size=batch_size,
                             learning_rate=lr, optimizer="Adam", loss="mse"),
        epochs_run=len(history.rows),
        best_epoch=min(history.rows, key=lambda r: r["val_loss"])["epoch"],
        history={"val_loss": [r["val_loss"] for r in history.rows]},
    )


def load_predict(name: str, X, output_dir: str | Path = "models") -> np.ndarray:
    """Predict from a project-created artifact; preprocessing remains caller-owned."""
    name = name.lower()
    folder = Path(output_dir)
    meta = json.loads((folder / f"{name}_metadata.json").read_text(encoding="utf-8"))
    x = np.asarray(X, dtype=np.float32)
    artifact = Path(meta["model_path"])
    if not artifact.exists():
        # Portable after moving the project directory.
        artifact = folder / artifact.name
    _seed(int(meta["seed"]))
    if name == "xgboost":
        from xgboost import XGBRegressor
        model = XGBRegressor()
        model.load_model(artifact)
        prediction = model.predict(x)
    elif name == "keras":
        os.environ["KERAS_BACKEND"] = "torch"
        import keras
        prediction = keras.models.load_model(artifact).predict(x, verbose=0)
    elif name == "tabnet":
        from pytorch_tabnet.tab_model import TabNetRegressor
        model = TabNetRegressor(device_name="cpu", verbose=0)
        model.load_model(str(artifact))
        prediction = model.predict(x)
    elif name in {"flash", "fastai"}:
        import torch
        if name == "flash":
            model = _dense_torch_model(int(meta["n_features"]))
        else:
            from fastai.tabular.model import TabularModel
            model = TabularModel([], int(meta["n_features"]), 1, [64, 32],
                                 ps=[0.1, 0.0], use_bn=False, bn_cont=False)
        model.load_state_dict(torch.load(artifact, map_location="cpu", weights_only=True))
        model.eval()
        with torch.no_grad():
            tensor = torch.from_numpy(x)
            if name == "fastai":
                prediction = model(torch.empty((len(x), 0), dtype=torch.long), tensor).numpy()
            else:
                prediction = model(tensor).numpy()
    else:
        raise ValueError(f"Unknown model: {name}")
    result = np.asarray(prediction, dtype=float).reshape(-1)
    if not np.isfinite(result).all():
        raise RuntimeError("Nonfinite loaded-model predictions.")
    return result
