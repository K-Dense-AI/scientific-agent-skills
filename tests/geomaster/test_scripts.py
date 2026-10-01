from pathlib import Path
import importlib.util
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
import geopandas as gpd
from shapely.geometry import box, Point

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'geomaster'
spec = importlib.util.spec_from_file_location('geomaster_raster_workflows', SKILL_ROOT / 'scripts' / 'raster_workflows.py')
recipes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recipes)


def raster(path, data, *, crs='EPSG:32610', nodata=None):
    if data.ndim == 2:
        data = data[None]
    with rasterio.open(path, 'w', driver='GTiff', count=data.shape[0], height=data.shape[1], width=data.shape[2],
                       transform=from_origin(500000, 4200000, 10, 20), crs=crs, dtype=data.dtype, nodata=nodata) as ds:
        ds.write(data)


def test_unsigned_and_masked_difference():
    a=np.ma.array([1,3,0,5],mask=[0,0,0,1],dtype='uint16')
    b=np.array([3,1,0,4],dtype='uint16')
    np.testing.assert_allclose(recipes.normalized_difference(a,b),[-.5,.5,np.nan,np.nan],equal_nan=True)


def test_shapes_and_scales():
    with pytest.raises(ValueError): recipes.normalized_difference(np.zeros((2,1)),np.zeros(2))
    with pytest.raises(ValueError): recipes.spectral_indices(np.zeros(2),*[np.zeros(3)]*5)
    v=recipes.spectral_indices(*[np.array([x]) for x in [.1,.2,.2,.6,.3,.1]])
    assert v['NDVI'][0] == pytest.approx(.5)
    assert v['EVI'][0] == pytest.approx(2.5*.4/(.6+1.2-.75+1))
    assert v['NBR'][0] == pytest.approx(.5/.7)


@pytest.mark.parametrize('dx,dy,aspect',[(1,0,270),(0,1,180),(-1,0,90),(0,-1,0)])
def test_terrain_known_planes(dx,dy,aspect):
    rows,cols=np.mgrid[:5,:6]
    z=cols*10*dx + (-rows*20)*dy
    slope, direction, shade=recipes.terrain_metrics(z,from_origin(0,0,10,20),'EPSG:32610')
    np.testing.assert_allclose(slope,45)
    np.testing.assert_allclose(direction,aspect)
    assert np.isfinite(shade).all() and (shade>=0).all() and (shade<=1).all()


def test_flat_shade_and_mask():
    z=np.ma.array(np.zeros((5,5)),mask=False)
    z.mask[2,2]=True
    slope,aspect,shade=recipes.terrain_metrics(z,from_origin(0,0,10,20),'EPSG:32610')
    assert np.isnan(aspect).all()
    assert np.isnan(slope[2,2]) and np.isnan(slope[1,2])
    assert shade[0,0]==pytest.approx(np.sqrt(.5))


@pytest.mark.parametrize('crs,transform', [('EPSG:4326',from_origin(0,0,1,1)),('EPSG:2227',from_origin(0,0,1,1)),('EPSG:32610',rasterio.Affine(10,1,0,0,-10,0))])
def test_terrain_rejects_invalid_units_or_grid(crs,transform):
    with pytest.raises(ValueError): recipes.terrain_metrics(np.ones((2,2)),transform,crs)


def test_ndvi_roundtrip(tmp_path):
    src,dst=tmp_path/'s2.tif',tmp_path/'ndvi.tif'
    raster(src,np.array([[[2000,0],[5000,4000]],[[6000,0],[1000,4000]]],dtype='uint16'),nodata=0)
    result=recipes.write_ndvi(src,dst,red_band=1,nir_band=2,scale=.0001,offset=-.1)
    assert result[0,0]==pytest.approx(2/3)
    assert np.isnan(result[0,1]) and result[1,1]==0
    with rasterio.open(dst) as ds:
        assert ds.count==1 and ds.dtypes==('float32',)
        assert ds.crs.to_epsg()==32610 and ds.transform.e==-20
        assert ds.read(1,masked=True).mask[0,1]
    with pytest.raises(ValueError): recipes.write_ndvi(src,src,red_band=1,nir_band=2,scale=1,offset=0)


@pytest.mark.parametrize('band,scale',[(0,1),(3,1),(True,1),(1,0),(1,float('nan'))])
def test_ndvi_rejects_bad_parameters(tmp_path,band,scale):
    p=tmp_path/'in.tif';raster(p,np.ones((2,2,2),dtype='uint16'))
    with pytest.raises(ValueError): recipes.write_ndvi(p,tmp_path/'out.tif',red_band=band,nir_band=2,scale=scale,offset=0)


def training():
    return gpd.GeoDataFrame({'class_id':[1,300]},geometry=[box(500000,4199920,500020,4200000),box(500020,4199920,500040,4200000)],crs=32610)


def test_classification_preserves_large_labels_mask_and_reprojects(tmp_path):
    p=tmp_path/'in.tif';q=tmp_path/'out.tif'
    data=np.tile([10,10,100,100],(4,1)).astype('uint16');data[0,0]=0
    raster(p,data,nodata=0)
    model=recipes.classify_imagery(p,training().to_crs(4326),q)
    assert list(model.classes_)==[1,300]
    with rasterio.open(q) as ds:
        out=ds.read(1,masked=True)
        assert out.mask[0,0] and ds.nodata==0 and ds.dtypes==('uint16',)
        assert (out[:,2:]==300).all() and out[1,0]==1


@pytest.mark.parametrize('failure',['missing_crs','bad_label','overlap','no_pixels','point','empty'])
def test_classification_rejects_bad_training(tmp_path,failure):
    p=tmp_path/'in.tif';raster(p,np.ones((4,4),dtype='uint16'))
    t=training()
    if failure=='missing_crs': t=t.set_crs(None,allow_override=True)
    if failure=='bad_label': t.loc[0,'class_id']=0
    if failure=='overlap': t.loc[1,'geometry']=t.geometry.iloc[0]
    if failure=='no_pixels': t.loc[0,'geometry']=box(0,0,1,1)
    if failure=='point': t.loc[0,'geometry']=Point(500000,4200000)
    if failure=='empty': t=t.iloc[:0]
    with pytest.raises(ValueError): recipes.classify_imagery(p,t,tmp_path/'out.tif')


def test_writers_refuse_existing_output_and_same_band(tmp_path):
    src=tmp_path/'source.tif';dst=tmp_path/'output.tif'
    raster(src,np.ones((2,4,4),dtype='uint16'))
    dst.write_bytes(b'preserve existing result')
    with pytest.raises(ValueError,match='already exists'):
        recipes.write_ndvi(src,dst,red_band=1,nir_band=2,scale=1,offset=0)
    with pytest.raises(ValueError,match='already exists'):
        recipes.classify_imagery(src,training(),dst)
    assert dst.read_bytes()==b'preserve existing result'
    with pytest.raises(ValueError,match='distinct'):
        recipes.write_ndvi(src,tmp_path/'new.tif',red_band=1,nir_band=1,scale=1,offset=0)


def test_writers_refuse_hardlink_alias(tmp_path):
    import os
    src=tmp_path/'source.tif';alias=tmp_path/'alias.tif'
    raster(src,np.ones((2,4,4),dtype='uint16')); before=src.read_bytes()
    os.link(src,alias)
    with pytest.raises(ValueError): recipes.write_ndvi(src,alias,red_band=1,nir_band=2,scale=1,offset=0)
    with pytest.raises(ValueError): recipes.classify_imagery(src,training(),alias)
    assert src.read_bytes()==before
