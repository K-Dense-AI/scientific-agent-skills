"""Execute scientific behaviors from maintained docs using tiny local fixtures."""
from pathlib import Path
import ast
import re
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import pytest
from shapely.geometry import Point, LineString, box

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'geomaster'


def recipe(file,name,**namespace):
    scope={'np':np,'pd':pd,'nx':nx,**namespace}
    for code in re.findall(r'```python\n(.*?)```',(SKILL_ROOT/'references'/file).read_text(),re.S):
        tree=ast.parse(code)
        nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name]
        if nodes:
            exec(compile(ast.Module(body=nodes,type_ignores=[]),str(file),'exec'),scope)
            return scope[name]
    raise AssertionError(f'{name} not found in {file}')


def test_population_conservation_and_empty_support():
    allocate=recipe('industry-applications.md','redistribute_population')
    np.testing.assert_allclose(allocate(100,np.array([[1,2],[0,1]])),[[25,50],[0,25]])
    assert allocate(0,np.zeros(3)).sum()==0
    with pytest.raises(ValueError): allocate(1,np.zeros(3))
    with pytest.raises(ValueError): allocate(1,[1,-1])


def test_walk_time_uses_metres_and_seconds():
    reachable=recipe('industry-applications.md','reachable_walk_nodes')
    g=nx.MultiDiGraph();g.add_edge(0,1,length=50);g.add_edge(1,2,length=100)
    assert reachable(g,0,minutes=1,speed_kph=3.6)=={0:0,1:50}
    assert 'walk_seconds' not in g[0][1][0]


def test_variogram_excludes_diagonal_self_pairs():
    from scipy.spatial.distance import pdist
    variogram=recipe('specialized-topics.md','empirical_variogram',pdist=pdist)
    lag,gamma=variogram([[0,0],[1,0]],[0,2],max_lag=2,n_lags=1)
    np.testing.assert_allclose(lag,[1]);np.testing.assert_allclose(gamma,[2])


def test_lineage_cycle_terminates():
    lineage=recipe('specialized-topics.md','DataLineage')()
    lineage.record_transformation('a','one','b',{})
    lineage.record_transformation('b','two','a',{})
    assert len(lineage.get_lineage('a'))==2


def test_red_edge_spacing_mask_and_window_validation():
    function=recipe('remote-sensing.md','red_edge_position')
    wavelengths=np.array([670,680,700,750,760])
    cube=(wavelengths/100)[None,None,:]**2
    result=function(cube,wavelengths)
    assert result[0,0]==750
    with pytest.raises(ValueError): function(cube,wavelengths[::-1])
    cube[:]=np.nan;assert np.isnan(function(cube,wavelengths)).all()


def test_sar_power_masking():
    function=recipe('remote-sensing.md','power_to_db')
    values=function(np.ma.array([1,10,0,-1,100],mask=[0,0,0,0,1]))
    np.testing.assert_allclose(values,[0,10,np.nan,np.nan,np.nan],equal_nan=True)


def test_temperature_descending_latitude_and_current_time_name():
    import xarray as xr
    function=recipe('scientific-domains.md','subset_temperature')
    ds=xr.Dataset({'t2m':(('valid_time','latitude','longitude'),np.full((2,3,2),280.))},
                  coords={'valid_time':pd.date_range('2023-01-01',periods=2),'latitude':[30.,25.,20.],'longitude':[65.,70.]})
    out=function(ds,65,20,70,30)
    assert out.sizes=={'valid_time':1,'latitude':3,'longitude':2}
    np.testing.assert_allclose(out,6.85)


def test_noded_crossing_really_connects():
    from shapely import node,get_parts
    from shapely.geometry import MultiLineString
    function=recipe('advanced-gis.md','planar_graph',node=node,get_parts=get_parts,MultiLineString=MultiLineString)
    graph=function([LineString([(0,0),(2,0)]),LineString([(1,-1),(1,1)])])
    assert len(graph.edges)==4
    assert nx.shortest_path_length(graph,(0,0),(1,1),weight='length')==2


def test_coordinate_reference_codes_and_roundtrip():
    from pyproj import CRS,Transformer,Geod
    for code,fragment in [(4283,'GDA94'),(3338,'Alaska'),(3112,'Geoscience Australia'),('ESRI:102003','Albers')]:
        assert fragment in CRS.from_user_input(code).name
    forward=Transformer.from_crs(4326,32610,always_xy=True)
    x,y=forward.transform(-122.4,37.7,errcheck=True)
    lon,lat=forward.transform(x,y,direction='INVERSE',errcheck=True)
    assert Geod(ellps='WGS84').inv(-122.4,37.7,lon,lat)[2]<.001
    nominal=recipe('coordinate-systems.md','get_utm_zone')
    assert nominal(180,0)=='EPSG:32660'
    with pytest.raises(ValueError): nominal(0,85)


def test_geoparquet_bbox_roundtrip(tmp_path):
    p=tmp_path/'points.parquet'
    gdf=gpd.GeoDataFrame({'id':[1,2]},geometry=[Point(0,0),Point(10,10)],crs=32610)
    gdf.to_parquet(p,index=False,write_covering_bbox=True,schema_version='1.1.0')
    out=gpd.read_parquet(p,bbox=(-1,-1,1,1))
    assert out.id.tolist()==[1] and out.crs.to_epsg()==32610


def test_rioxarray_dask_and_cog(tmp_path):
    import rasterio
    import rioxarray
    from rasterio.transform import from_origin
    from rasterio.shutil import copy as rio_copy
    from rio_cogeo.cogeo import cog_validate
    p=tmp_path/'input.tif';out=tmp_path/'out.tif'
    with rasterio.open(p,'w',driver='GTiff',count=1,width=4,height=4,dtype='uint16',nodata=0,crs=32610,transform=from_origin(0,40,10,10)) as ds:
        ds.write(np.arange(16,dtype='uint16').reshape(1,4,4))
    cube=rioxarray.open_rasterio(p,masked=True,chunks={'band':1,'x':2,'y':2})
    assert cube.chunks is not None and np.isnan(cube.isel(band=0,y=0,x=0).compute())
    assert float(cube.mean().compute())==8
    cube.close()
    rio_copy(p,out,driver='COG',compress='DEFLATE',overview_resampling='NEAREST')
    valid,errors,warnings=cog_validate(out)
    assert valid,errors
    with rasterio.open(out) as ds: assert ds.read(1,masked=True).mask[0,0]


def test_xarray_explicit_zarr2(tmp_path):
    import xarray as xr
    p=tmp_path/'data.zarr'
    ds=xr.Dataset({'value':(('y','x'),np.arange(6).reshape(2,3))})
    ds.to_zarr(p,mode='w-',zarr_format=2,consolidated=True)
    xr.testing.assert_equal(xr.open_zarr(p,consolidated=True).compute(),ds)
    with pytest.raises(Exception): ds.to_zarr(p,mode='w-',zarr_format=2)


def test_osmnx_synthetic_speeds_routing():
    import osmnx as ox
    graph=nx.MultiDiGraph(crs='EPSG:4326')
    graph.add_node(0,x=-122.4,y=37.7);graph.add_node(1,x=-122.3,y=37.7)
    graph.add_edge(0,1,length=100,highway='residential',maxspeed='36')
    graph=ox.routing.add_edge_speeds(graph)
    graph=ox.routing.add_edge_travel_times(graph)
    assert graph[0][1][0]['travel_time']==pytest.approx(10)
    assert ox.distance.nearest_nodes(graph,-122.4,37.7)==0
    assert nx.shortest_path(graph,0,1,weight='travel_time')==[0,1]


def test_movingpandas_documented_methods():
    import movingpandas as mpd
    gdf=gpd.GeoDataFrame({'track_id':[1]*4,'timestamp':pd.date_range('2023-01-01',periods=4,freq='min')},
                        geometry=[Point(i,0) for i in range(4)],crs=32610)
    c=mpd.TrajectoryCollection(gdf,'track_id',t='timestamp')
    segments=mpd.ObservationGapSplitter(c).split(gap=pd.Timedelta(hours=1))
    simplified=mpd.DouglasPeuckerGeneralizer(segments).generalize(tolerance=10)
    stops=mpd.TrajectoryStopDetector(c).get_stop_points(max_diameter=100,min_duration=pd.Timedelta(minutes=1))
    moving=mpd.StopSplitter(c).split(max_diameter=100,min_duration=pd.Timedelta(minutes=1),min_length=0)
    assert len(segments)==1 and len(simplified)==1 and len(stops)==1
    assert len(moving)==0


def test_kriging_and_local_weights():
    from pykrige.ok import OrdinaryKriging
    from libpysal.weights import KNN
    from esda.getisord import G_Local
    coords=np.array([[0,0],[1,0],[0,1],[1,1],[2,0],[2,1]],dtype=float)
    values=np.array([1,2,2,3,3,4],dtype=float)
    kriging=OrdinaryKriging(coords[:,0],coords[:,1],values,variogram_model='linear')
    prediction,variance=kriging.execute('points',coords[:,0],coords[:,1])
    np.testing.assert_allclose(prediction,values,atol=1e-8)
    w=KNN.from_array(coords,k=3)
    local=G_Local(values,w,transform='B',star=True,permutations=9,seed=42,n_jobs=1,alternative='two-sided')
    assert local.p_sim.shape==values.shape and np.isfinite(local.p_sim).all()


def test_dask_geopandas_spatial_shuffle_join():
    import dask_geopandas as dgpd
    points=gpd.GeoDataFrame({'value':[1,2]},geometry=[Point(0,0),Point(5,5)],crs=32610)
    zones=gpd.GeoDataFrame({'zone_id':['a']},geometry=[box(-1,-1,1,1)],crs=32610)
    left=dgpd.from_geopandas(points,npartitions=2).spatial_shuffle()
    right=dgpd.from_geopandas(zones,npartitions=1).spatial_shuffle()
    joined=left.sjoin(right,how='inner',predicate='within').compute()
    assert joined.value.tolist()==[1] and joined.zone_id.tolist()==['a']


def test_fiona_geometry_roundtrip(tmp_path):
    import fiona
    p=tmp_path/'point.geojson'
    with fiona.open(p,'w',driver='GeoJSON',schema={'geometry':'Point','properties':{'name':'str'}},crs='EPSG:4326') as ds:
        ds.write({'geometry':{'type':'Point','coordinates':[0,0]},'properties':{'name':'Origin'}})
    with fiona.open(p) as ds:
        feature=next(iter(ds))
        assert feature['geometry']['coordinates']==(0.,0.) and feature['properties']['name']=='Origin'


def test_watershed_and_mercantile_contracts():
    from scipy.ndimage import label
    from skimage.segmentation import watershed
    import mercantile
    markers,count=label(np.array([[1,0,0],[0,0,0],[0,0,1]],dtype=bool))
    out=watershed(np.zeros((3,3)),markers=markers,mask=np.ones((3,3),dtype=bool))
    assert set(np.unique(out))=={1,2}
    tiles=list(mercantile.tiles(-122.41,37.70,-122.40,37.71,zooms=12))
    assert len(tiles)>=1 and all(tile.z==12 for tile in tiles)
