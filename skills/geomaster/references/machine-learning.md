# Machine Learning for Geospatial Data

Machine learning for remote sensing and spatial analysis, reviewed 2026-10-01.
RF arithmetic/masking is tested with synthetic rasters. Neural network, PyG and SHAP
examples are illustrative, source-reviewed templates; no training run or accuracy
claim is made. Install their packages separately. Record feature units, masks, band
order, normalization, labels and spatial/temporal split definitions.

## Traditional Machine Learning

### Random Forest for land cover

Use the bundled `classify_imagery` helper (see the main skill) for a small masked
raster fit/predict exercise. Rasterize labels in the raster CRS using its actual
transform. Exclude nodata from both fitting and prediction, reserve an output nodata
code and verify integer class range before casting.

For assessment, split at independent spatial/temporal units **before** fitting:

```python
from sklearn.model_selection import GroupShuffleSplit
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import numpy as np

# X, y and spatial_block_id have aligned rows, one row per valid labelled sample.
train, validation = next(GroupShuffleSplit(n_splits=1, test_size=0.2,
    random_state=42).split(X, y, groups=spatial_block_id))
if set(np.unique(y[validation])) - set(np.unique(y[train])):
    raise ValueError('Holdout contains classes absent from training')
model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=1)
model.fit(X[train], y[train])
print(classification_report(y[validation], model.predict(X[validation]), zero_division=0))
```

Random pixels from the same labelled polygon in both partitions leak spatial
information. Block size and buffer separation depend on autocorrelation and the
intended transfer region; grouping alone does not prove independence. Also report
held-out sample/area support, imbalance and uncertainty. Feature importance is model
association, not causal evidence.

### Support Vector Machine

```python
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler

def svm_classifier(X_train, y_train):
    """SVM classifier for remote sensing."""

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    # Train SVM
    svm = SVC(
        kernel='rbf',
        C=100,
        gamma='scale',
        class_weight='balanced',
        probability=True
    )
    svm.fit(X_train_scaled, y_train)

    return svm, scaler

# Multi-class classification
def multiclass_svm(X_train, y_train):
    from sklearn.multiclass import OneVsRestClassifier

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    svm_ovr = OneVsRestClassifier(
        SVC(kernel='rbf', C=10, probability=True),
        n_jobs=-1
    )
    svm_ovr.fit(X_train_scaled, y_train)

    return svm_ovr, scaler
```

## Deep Learning

### CNN tensor example (PyTorch)

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader

# Define CNN
class LandCoverCNN(nn.Module):
    def __init__(self, in_channels=12, num_classes=10):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(in_channels, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2),

            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(2),

            nn.Conv2d(128, 256, 3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )

        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(256, 128, 2, stride=2),
            nn.BatchNorm2d(128),
            nn.ReLU(),

            nn.ConvTranspose2d(128, 64, 2, stride=2),
            nn.BatchNorm2d(64),
            nn.ReLU(),

            nn.ConvTranspose2d(64, num_classes, 2, stride=2),
        )

    def forward(self, x):
        x = self.encoder(x)
        x = self.decoder(x)
        return x

# Training
def train_model(train_loader, val_loader, num_epochs=50):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = LandCoverCNN().to(device)

    criterion = nn.CrossEntropyLoss(ignore_index=-1)  # explicit nodata label
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    for epoch in range(num_epochs):
        model.train()
        train_loss = 0

        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()

        # Validation
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = criterion(outputs, labels)
                val_loss += loss.item()

        print(f'Epoch {epoch+1}/{num_epochs}, Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}')

    return model
```

### U-Net for Semantic Segmentation

Inputs are `(N,C,H,W)` float tensors; labels are `(N,H,W)` integer class IDs.
This architecture requires H/W divisible by 16; pad/crop with a recorded policy.
The simpler CNN above requires divisibility by 8. Neither model is pretrained.

```python
class UNet(nn.Module):
    def __init__(self, in_channels=4, num_classes=5):
        super().__init__()

        # Encoder
        self.enc1 = self.conv_block(in_channels, 64)
        self.enc2 = self.conv_block(64, 128)
        self.enc3 = self.conv_block(128, 256)
        self.enc4 = self.conv_block(256, 512)

        # Bottleneck
        self.bottleneck = self.conv_block(512, 1024)

        # Decoder
        self.up1 = nn.ConvTranspose2d(1024, 512, 2, stride=2)
        self.dec1 = self.conv_block(1024, 512)

        self.up2 = nn.ConvTranspose2d(512, 256, 2, stride=2)
        self.dec2 = self.conv_block(512, 256)

        self.up3 = nn.ConvTranspose2d(256, 128, 2, stride=2)
        self.dec3 = self.conv_block(256, 128)

        self.up4 = nn.ConvTranspose2d(128, 64, 2, stride=2)
        self.dec4 = self.conv_block(128, 64)

        # Final layer
        self.final = nn.Conv2d(64, num_classes, 1)

    def conv_block(self, in_ch, out_ch):
        return nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        # Encoder
        e1 = self.enc1(x)
        e2 = self.enc2(F.max_pool2d(e1, 2))
        e3 = self.enc3(F.max_pool2d(e2, 2))
        e4 = self.enc4(F.max_pool2d(e3, 2))

        # Bottleneck
        b = self.bottleneck(F.max_pool2d(e4, 2))

        # Decoder with skip connections
        d1 = self.dec1(torch.cat([self.up1(b), e4], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d1), e3], dim=1))
        d3 = self.dec3(torch.cat([self.up3(d2), e2], dim=1))
        d4 = self.dec4(torch.cat([self.up4(d3), e1], dim=1))

        return self.final(d4)
```

### Change Detection with Siamese Network

```python
class SiameseNetwork(nn.Module):
    """Siamese network for change detection."""

    def __init__(self):
        super().__init__()
        self.feature_extractor = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),

            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2),

            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
        )

        self.classifier = nn.Sequential(
            nn.Conv2d(384, 128, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(128, 64, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 2, 1),  # Binary: change / no change
        )

    def forward(self, x1, x2):
        f1 = self.feature_extractor(x1)
        f2 = self.feature_extractor(x2)

        # Concatenate features
        diff = torch.abs(f1 - f2)
        combined = torch.cat([f1, f2, diff], dim=1)

        logits = self.classifier(combined)
        return F.interpolate(logits, size=x1.shape[-2:], mode='bilinear', align_corners=False)
```

## Graph Neural Networks

### PyTorch Geometric for Spatial Data

```python
import torch
import numpy as np
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv

# Create spatial graph
def create_spatial_graph(points_gdf, feature_columns, k_neighbors=5):
    """Create graph from point data using k-NN."""

    from sklearn.neighbors import NearestNeighbors

    if points_gdf.crs is None or not points_gdf.crs.is_projected:
        raise ValueError('Use a justified metric CRS for Euclidean neighbours')
    if not 1 <= k_neighbors < len(points_gdf):
        raise ValueError('k must be between 1 and n-1')
    coords = np.array([[p.x, p.y] for p in points_gdf.geometry])

    # Find k-nearest neighbors
    nbrs = NearestNeighbors(n_neighbors=k_neighbors + 1).fit(coords)
    distances, indices = nbrs.kneighbors(coords)

    # Create edge index
    edge_index = []
    for i, neighbors in enumerate(indices):
        for j in neighbors:
            if i != j:
                edge_index.append([j, i])  # neighbour sends message to the query node

    edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous()

    # Node features
    features = points_gdf[feature_columns].to_numpy(dtype=float)
    if not np.isfinite(features).all():
        raise ValueError('Features must be finite numeric predictors; exclude target and IDs')
    x = torch.tensor(features, dtype=torch.float)

    return Data(x=x, edge_index=edge_index)

# GCN for spatial prediction
class SpatialGCN(torch.nn.Module):
    def __init__(self, num_features, hidden_channels=64):
        super().__init__()
        self.conv1 = GCNConv(num_features, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, hidden_channels)
        self.conv3 = GCNConv(hidden_channels, 1)

    def forward(self, data):
        x, edge_index = data.x, data.edge_index
        x = self.conv1(x, edge_index).relu()
        x = F.dropout(x, p=0.5, training=self.training)
        x = self.conv2(x, edge_index).relu()
        x = self.conv3(x, edge_index)
        return x
```

## Explainable AI (XAI) for Geospatial

### SHAP for Model Interpretation

```python
import shap
import numpy as np

def explain_model(model, X, feature_names):
    """Explain model predictions using SHAP."""

    # Create explainer
    explainer = shap.Explainer(model, X)

    # Calculate SHAP values
    shap_values = explainer(X)

    # For multiclass outputs, select one class Explanation first.
    if shap_values.values.ndim != 2:
        raise ValueError('Select the intended model output/class before plotting')
    shap.plots.beeswarm(shap_values)
    for i in range(X.shape[1]):
        shap.plots.scatter(shap_values[:, i])

    return shap_values

```

Averaging SHAP values over neighbours is a descriptive spatial summary, not a
correction for autocorrelation or causal explanation. Define a compatible background
sample, model output scale and held-out interpretation set. Explanations can shift
when correlated features or background support change.

### Attention Maps for CNNs

Grad-CAM requires activations and gradients for a chosen layer and a defined scalar
target. Generic `nn.Module` has no `get_gradient` or `get_activation` methods. Register
forward/backward hooks (and remove them), retain the intended target gradient, pool
spatial gradients and combine with the captured activation. For segmentation choose
class and pixel/region explicitly; `argmax` over every output axis is not a class index.
Check shape, zero normalization range and detach before converting to NumPy.

TorchGeo adds geospatial datasets/samplers, not an automatic scientific training
pipeline. Follow its versioned dataset documentation, labels and preprocessing; keep
region/scene separation when defining samplers. No model weights were downloaded.

Sources: [GroupShuffleSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupShuffleSplit.html),
[SHAP plots](https://shap.readthedocs.io/en/latest/generated/shap.plots.beeswarm.html),
[PyTorch Conv2d](https://docs.pytorch.org/docs/stable/generated/torch.nn.Conv2d.html),
[TorchGeo docs](https://torchgeo.readthedocs.io/en/stable/),
[PyG GCNConv](https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.nn.conv.GCNConv.html).

For more ML examples, see [code-examples.md](code-examples.md).
