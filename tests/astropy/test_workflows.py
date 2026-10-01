"""Small scientific regressions for the Astropy skill, without remote data."""
from pathlib import Path
import pytest

np = pytest.importorskip("numpy")

pytest.importorskip('astropy')
from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, FK5, SkyCoord
from astropy.io import fits
from astropy.table import MaskedColumn, QTable, Table, unique
from astropy.time import Time
from astropy.utils import iers
from astropy.wcs import WCS

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'astropy'

@pytest.fixture(autouse=True)
def offline_iers():
    with iers.conf.set_temp('auto_download', False):
        yield


def test_unit_equivalencies_and_aliasing():
    wavelength = 500 * u.nm
    frequency = wavelength.to(u.Hz, equivalencies=u.spectral())
    assert frequency.to_value(u.Hz) == pytest.approx(5.99584916e14)
    assert frequency.to_value(u.nm, equivalencies=u.spectral()) == pytest.approx(500)
    velocity = 1000 * u.km/u.s
    observed = velocity.to(u.Hz, equivalencies=u.doppler_optical(wavelength))
    assert observed.to_value(u.km/u.s, equivalencies=u.doppler_optical(wavelength)) == pytest.approx(1000)
    assert (-2.5*u.mag(u.ct/u.s)).physical.to_value(u.ct/u.s) == pytest.approx(10)
    values = np.arange(3.0)
    quantity = values << (u.m/u.s)
    assert np.shares_memory(values, quantity.value)
    fortnight = u.def_unit('bakers_fortnight', 13*u.day)
    with u.add_enabled_units([fortnight]):
        assert u.Quantity('2 bakers_fortnight').to_value(u.day) == 26


def test_coordinate_frames_and_synthetic_catalog_matching():
    pytest.importorskip('scipy')
    coords = SkyCoord([10, 11, 12]*u.deg, [41, -5, 42]*u.deg, frame='icrs')
    back = coords.galactic.icrs
    assert np.max(coords.separation(back).to_value(u.arcsec)) < 1e-8
    assert coords.transform_to(FK5(equinox='J1975')).shape == (3,)
    catalog = SkyCoord([10, 10.0001, 30]*u.deg, [0, 0, 0]*u.deg)
    targets = SkyCoord([10.00001, 10.00002]*u.deg, [0, 0]*u.deg)
    idx, sep, chord = targets.match_to_catalog_sky(catalog)
    assert idx.tolist() == [0, 0]  # nearest neighbors need not be one-to-one
    assert np.all(sep < 1*u.arcsec)
    assert chord.unit == u.one
    table = QTable({'ra': [40, 44]*u.arcmin, 'dec': [60, 120]*u.arcmin})
    from_columns = SkyCoord(table['ra'], table['dec'], unit=u.deg, frame='icrs')
    assert np.allclose(from_columns.ra.deg, [2/3, 11/15])


def test_altaz_and_space_motion():
    location = EarthLocation(lat=40.8*u.deg, lon=-121.5*u.deg, height=1060*u.m)
    time = Time('2023-01-15 23:00:00', scale='utc')
    source = SkyCoord(10.68*u.deg, 41.27*u.deg)
    horizontal = source.transform_to(AltAz(obstime=time, location=location, pressure=0*u.hPa))
    assert np.isfinite(horizontal.alt.deg)
    assert source.separation(horizontal.icrs).to_value(u.arcsec) < 1e-5
    moving = SkyCoord(10*u.deg, 41*u.deg, distance=150*u.pc,
                      pm_ra_cosdec=15*u.mas/u.yr, pm_dec=5*u.mas/u.yr,
                      radial_velocity=20*u.km/u.s, obstime=Time('J2000'))
    propagated = moving.apply_space_motion(new_obstime=Time('J2010'))
    assert moving.separation(propagated).to_value(u.mas) == pytest.approx(np.hypot(15,5)*10, rel=1e-4)


def test_times_same_instant_leap_second_precision_and_masks():
    t = Time('2023-01-15 12:00:00', scale='utc')
    assert (t.tai-t.utc).to_value(u.s) == pytest.approx(0, abs=1e-12)
    assert t.tai.iso == '2023-01-15 12:00:37.000'
    before = Time('2016-12-31 23:59:59', scale='utc')
    after = Time('2017-01-01 00:00:00', scale='utc')
    assert (after-before).to_value(u.s) == pytest.approx(2, abs=1e-10)
    precise = Time('2023-01-15 12:30:45.123456789', scale='utc')
    restored = Time(precise.jd1, precise.jd2, format='jd', scale=precise.scale)
    assert abs((restored-precise).to_value(u.ns)) < 0.01
    times = Time(['2023-01-01','2023-06-01','2023-12-31'], scale='utc')
    times[1] = np.ma.masked
    assert len(times[~times.mask]) == 2
    assert len(times.unmasked) == 3
    assert not np.any(times.filled(Time('2000-01-01',scale='utc')).mask)


def test_barycentric_corrections_use_location_once():
    location = EarthLocation(lat=40*u.deg, lon=-120*u.deg, height=1000*u.m)
    times = Time(['2023-01-15 08:30:00','2023-01-16 08:30:00'], scale='utc', location=location)
    target = SkyCoord(ra='23h23m08.55s', dec='+18d24m59.3s')
    correction = times.light_travel_time(target, kind='barycentric')
    bary = times.tdb + correction
    assert bary.scale == 'tdb'
    assert np.all(np.abs(correction.to_value(u.s)) < 510)
    assert np.allclose((bary-times.tdb).to_value(u.s),correction.to_value(u.s),atol=1e-9)
    velocity = target.radial_velocity_correction(obstime=times)
    assert np.all(np.isfinite(velocity.to_value(u.m/u.s)))
    with pytest.raises(ValueError):
        target.radial_velocity_correction(obstime=times,location=location)
    assert np.all(np.isfinite(times.sidereal_time('apparent').value))
    assert np.all(np.isfinite(times.earth_rotation_angle().value))


def test_cosmology_distances_and_inverse_branches():
    pytest.importorskip('scipy')
    from astropy.cosmology import Planck18, FlatLambdaCDM, z_at_value
    z = np.array([0.1, 1.5, 2.0])
    assert u.allclose(Planck18.luminosity_distance(z),(1+z)**2*Planck18.angular_diameter_distance(z),rtol=1e-12)
    size = (Planck18.angular_diameter_distance(2)*(1*u.arcsec).to_value(u.rad)).to(u.kpc)
    assert size.value == pytest.approx(8.5782753094,rel=1e-8)
    low = z_at_value(Planck18.angular_diameter_distance,1500*u.Mpc,zmax=1.5)
    high = z_at_value(Planck18.angular_diameter_distance,1500*u.Mpc,zmin=2.5,zmax=10)
    assert 0 < low.value < 1.5 < 2.5 < high.value < 10
    assert u.allclose(Planck18.angular_diameter_distance([low.value,high.value]),1500*u.Mpc,rtol=1e-7)
    assert u.allclose(Planck18.age(z)+Planck18.lookback_time(z),Planck18.age(0),rtol=1e-10)
    changed = FlatLambdaCDM(70,0.3,name='Base model').clone(name='Modified H0',H0=72*u.km/u.s/u.Mpc)
    assert changed.H0.value == 72
    assert Planck18.differential_comoving_volume(1).unit == u.Mpc**3/u.sr


def test_fits_image_hdus_headers_cutout_checksums_and_copy(tmp_path):
    data = np.arange(80,dtype=np.float32).reshape(8,10)
    path = tmp_path/'observation.fits'
    primary = fits.PrimaryHDU()
    science = fits.ImageHDU(data,name='SCI')
    science.header['EXPTIME'] = 30.0
    science.header['BUNIT'] = 'adu'
    fits.HDUList([primary,science]).writeto(path,checksum=True)
    with fits.open(path,checksum=True) as hdul:
        hdul.verify('exception')
        assert hdul['SCI'].verify_checksum() == 1
        assert np.array_equal(hdul['SCI'].section[2:4,3:6],data[2:4,3:6])
        copied = hdul['SCI'].data.copy()
    assert np.array_equal(copied,data)
    read,header = fits.getdata(path,extname='SCI',header=True)
    assert header['BUNIT'] == 'adu' and np.array_equal(read,data)
    fits.setval(path,'OBSERVER',value='Synthetic',ext=0)
    assert fits.getval(path,'OBSERVER',ext=0) == 'Synthetic'


def test_fits_logical_null_and_variable_length_roundtrip(tmp_path):
    path = tmp_path/'logical.fits'
    cols = [fits.Column(name='flag',format='L',array=np.array([b'T',b'F',b''],dtype='S1')),
            fits.Column(name='variable',format='PL',array=[[True,False],[False],[True]])]
    fits.BinTableHDU.from_columns(cols).writeto(path)
    with fits.open(path,logical_as_bytes=True) as hdul:
        assert hdul[1].data['flag'].tolist() == [b'T',b'F',b'']
        assert hdul[1].data['variable'][0].tolist() == [b'T',b'F']


def test_table_unique_joins_copy_and_index_roundtrip(tmp_path):
    from astropy.table import join, hstack, vstack
    t = Table({'id':[1,1,2], 'ra':[10.0,10.0,11.0], 'dec':[2.0,2.0,3.0]})
    assert len(unique(t,keys='id')) == 2
    assert len(unique(t,keys=['ra','dec'])) == 2
    copy = t['ra','dec']; copy['ra'][0]=999
    assert t['ra'][0] == 10
    view = t[1:3]; view['ra'][0]=12
    assert t['ra'][1] == 12
    assert len(join(t,Table({'id':[1,2],'value':[5,6]}),keys='id')) == 3
    assert len(vstack([t,t])) == 6
    assert len(hstack([t,Table({'extra':[7,8,9]})]).colnames) == 4
    indexed=QTable({'id':[3,1,2], 'flux':[1,2,3]*u.Jy})
    indexed.add_index('id')
    indexed.write(tmp_path/'indexed.ecsv',format='ecsv',write_indices=True)
    restored=QTable.read(tmp_path/'indexed.ecsv',format='ecsv')
    assert restored.loc.with_index('id')[1]['flux'] == 2*u.Jy


def test_table_masks_units_and_time_roundtrips(tmp_path):
    t=QTable({'flux':MaskedColumn([1.0,2.0,3.0],mask=[False,True,False],unit=u.Jy),
              'time':Time(['2023-01-01','2023-01-02','2023-01-03'],scale='tt')})
    for suffix,fmt in [('ecsv','ascii.ecsv'),('fits','fits')]:
        path=tmp_path/f'table.{suffix}'
        t.write(path,format=fmt,serialize_method={'flux':'data_mask','time':'jd1_jd2'})
        kw={'astropy_native':True} if fmt=='fits' else {}
        restored=QTable.read(path,format=fmt,**kw)
        assert restored['flux'].unit == u.Jy
        assert restored['flux'].mask.tolist() == [False,True,False]
        assert restored['time'].scale == 'tt'
        assert np.allclose((restored['time']-t['time']).to_value(u.ns),0,atol=0.01)


def test_optional_hdf5_pandas_and_dask_small_roundtrips(tmp_path):
    pytest.importorskip('h5py'); pd=pytest.importorskip('pandas'); da=pytest.importorskip('dask.array')
    table=Table.from_pandas(pd.DataFrame({'id':[1,2], 'value':[3.0,4.0]}))
    assert table.to_pandas()['value'].tolist()==[3.0,4.0]
    table['value'].unit=u.Jy
    path=tmp_path/'table.hdf5'
    table.write(path,path='/data/table',serialize_meta=True)
    assert Table.read(path,path='/data/table')['value'].unit == u.Jy
    path=tmp_path/'dask.fits'
    fits.writeto(path,da.ones((8,8),chunks=(4,4)))
    assert np.all(fits.getdata(path) == 1)


def test_wcs_origin_array_order_and_footprint():
    wcs=WCS(naxis=2)
    wcs.wcs.crpix=[512,512];wcs.wcs.crval=[10.5,41.2]
    wcs.wcs.ctype=['RA---TAN','DEC--TAN'];wcs.wcs.cdelt=[-0.0001,0.0001]
    wcs.wcs.cunit=['deg','deg'];wcs.array_shape=(1024,1024)
    world=wcs.pixel_to_world(511,511)
    assert np.allclose([world.ra.deg,world.dec.deg],[10.5,41.2],atol=1e-10)
    x,y=wcs.world_to_pixel(world)
    assert np.allclose([x,y],[511,511],atol=1e-7)
    assert wcs.world_to_array_index(wcs.pixel_to_world(100,200)) == (200,100)
    assert np.allclose(wcs.all_pix2world([[512,512]],1),[[10.5,41.2]])
    assert wcs.calc_footprint().shape == (4,2)
    assert len(wcs.proj_plane_pixel_scales()) == 2
    assert wcs.pixel_scale_matrix.shape == (2,2)


def test_model_fitting_and_compound_parameter_names():
    pytest.importorskip('scipy')
    from astropy.modeling import models,fitting
    x=np.linspace(0,10,100)
    truth=models.Gaussian1D(amplitude=10,mean=5,stddev=1)
    noisy=truth(x)+np.random.default_rng(42).normal(0,0.5,x.shape)
    fitted=fitting.TRFLSQFitter()(models.Gaussian1D(amplitude=8,mean=4,stddev=1.5),x,noisy)
    assert abs(fitted.mean.value-5) < 0.05
    assert abs(fitted.stddev.value-1) < 0.05
    summed=models.Gaussian1D(amplitude=5,mean=3,stddev=1)+models.Gaussian1D(amplitude=8,mean=7,stddev=1.5)
    composite=truth | models.Scale(factor=2)
    assert np.allclose(composite(x),2*truth(x)) and np.all(np.isfinite(summed(x)))


def test_ccd_visualization_convolution_statistics_and_constants(tmp_path):
    pytest.importorskip('matplotlib')
    from astropy.nddata import CCDData,StdDevUncertainty
    from astropy.visualization import simple_norm,ImageNormalize,ZScaleInterval,AsinhStretch,PercentileInterval
    from astropy.convolution import convolve,convolve_fft,Gaussian2DKernel
    from astropy.stats import sigma_clip,sigma_clipped_stats,mad_std,biweight_location,biweight_scale
    from astropy import constants as const
    data=np.linspace(1,2,225).reshape(15,15)
    ccd=CCDData(data,unit=u.adu,uncertainty=StdDevUncertainty(np.ones_like(data)*0.1))
    ccd.write(tmp_path/'ccd.fits')
    restored=CCDData.read(tmp_path/'ccd.fits')
    assert restored.unit==u.adu and np.array_equal(restored.uncertainty.array,ccd.uncertainty.array)
    kernel=Gaussian2DKernel(x_stddev=2)
    assert np.allclose(convolve(data,kernel),convolve_fft(data,kernel),atol=1e-12)
    assert np.isfinite(simple_norm(data,'sqrt',percent=99)(data)).all()
    assert np.isfinite(ImageNormalize(data,interval=ZScaleInterval(),stretch=AsinhStretch())(data)).all()
    assert len(PercentileInterval(90).get_limits(data))==2
    sample=np.r_[np.random.default_rng(42).normal(size=1000),100]
    assert sigma_clip(sample,sigma=3,maxiters=5).mask[-1]
    assert np.all(np.isfinite(sigma_clipped_stats(sample)))
    assert np.isfinite([mad_std(sample),biweight_location(sample),biweight_scale(sample)]).all()
    radius=(2*const.G*(10*const.M_sun)/const.c**2).to_value(u.km)
    assert 29 < radius < 30
