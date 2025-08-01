Changelog
=========

Version 0.15
------------
| **Date:** July 4, 2025
| **Release:** v0.15

News
^^^^
Starting with CHAOS-8.3, the model of the ionospheric E-layer field
can be evaluated directly in ChaosMagPy
(see :meth:`chaosmagpy.chaos.CHAOS.synth_values_ion`) by simply loading the
MAT-file. However, this requires the installation of the optional package
`Apexpy <https://apexpy.readthedocs.io/en/latest/installation.html>`_.

Features
^^^^^^^^
* Updated built-in RC-index file to RC_1997-2025_June25_v6_allLT.dat (used
  during the construction of CHAOS-8.3).
* Added method to evaluate the ionospheric E-layer field
  :meth:`chaosmagpy.chaos.CHAOS.synth_values_ion`.

Version 0.14
------------
| **Date:** June 21, 2024
| **Release:** v0.14

News
^^^^
At the moment, only Numpy <= 1.26 is supported due to a deprecation affecting
a ChaosMagPy dependency. This will hopefully be fixed in the near future.

Features
^^^^^^^^
* Updated RC-index file to RC_1997-2024_June24_v5.dat (used during the
  construction of CHAOS-7.18).
* Increased precision of :func:`chaosmagpy.data_utils.timestamp` and
  :func:`chaosmagpy.data_utils.mjd2000` to nanosecond.
* Added function to compute the unit base vector in the direction of the
  geomagetic north pole: :func:`chaosmagpy.coordinate_utils.dipole_to_vec`.

Version 0.13.1
--------------
| **Date:** June 4, 2024
| **Release:** v0.13.1

Features
^^^^^^^^
* Made Matplotlib an optional dependency of ChaosMagPy.
* Added optional dependencies to ``pyproject.toml``.

Bugfixes
^^^^^^^^
* Removed deprecated matplotlib call to register a colormap. The previous
  version caused an ImportError with matplotlib >=3.9.

Version 0.13
------------
| **Date:** January 31, 2024
| **Release:** v0.13

Features
^^^^^^^^
* Updated RC-index file to RC_1997-2023_Dec23_v5.dat (used during the
  construction of CHAOS-7.17).
* Extended :func:`chaosmagpy.coordinate_utils.geo_to_gg` and
  :func:`chaosmagpy.coordinate_utils.gg_to_geo` to also allow for the
  rotation of vector components.
* Removed Cartopy from the dependencies (basic map projections are done with
  Matplotlib and coastlines are loaded from Natural Earth). New dependency for
  reading the coastline shapefile is PyShp (>=2.3.1).
* Added function :func:`chaosmagpy.chaos.load_IGRF_txtfile` to load the IGRF
  model from the coefficient TXT-file.

Version 0.12
------------
| **Date:** April 27, 2023
| **Release:** v0.12

Features
^^^^^^^^
* Updated RC-index file to RC_1997-2023_Feb_v8_Dst_mod.dat (used during the
  construction of CHAOS-7.14).
* Plotting function do not return figure and axes handles anymore. If needed,
  they can be accessed through matplotlib's ``gcf()`` and ``gca()``.
* Added function :func:`chaosmagpy.model_utils.sensitivity` to compute the
  sensitivity of spherical harmonic coefficients.
* Changed the default colormap for the component maps to ``'PuOr_r'`` (orange
  for positive values and purple for negative ones).

Bugfixes
^^^^^^^^
* Fixed error in :func:`chaosmagpy.data_utils.load_shcfile` when reading
  single piece, quadratic splines. Error was due to a failure to identify the
  shc-parameter line as the first non-comment line in the file.
* Fixed KeyError that is raised when no name is given to the
  :class:`chaosmagpy.chaos.CHAOS` constructor. This only affected direct calls
  to the constructor due to an outdated config keyword.

Version 0.11
------------
| **Date:** September 29, 2022
| **Release:** v0.11
| **Version of CHAOS:** CHAOS-7.12 (0712) and CHAOS-7.13 (0713)

Features
^^^^^^^^
* Updated RC-index file to RC_1997-2022_Sept_v3.dat.
* Improved time conversion paragraph in the usage section.
* Added option to :func:`chaosmagpy.coordinate_utils.sh_analysis` to increase
  the grid size for the numerical integration.
* Made time conversion functions (:func:`chaosmagpy.data_utils.mjd2000`,
  :func:`chaosmagpy.data_utils.timestamp`,
  :func:`chaosmagpy.data_utils.dyear_to_mjd`,
  :func:`chaosmagpy.data_utils.mjd_to_dyear`) directly available upon import.
* Extended :func:`chaosmagpy.model_utils.power_spectrum` to accept NumPy style
  ``axis`` keyword argument, and added new tests for this function.
* Added more detailed error message when requesting near-magnetospheric
  coefficients outside the domain covered by the RC-index file.
* Added input parameters ``rc_e`` and ``rc_i`` to the model call method.

Version 0.10
------------
| **Date:** July 1, 2022
| **Release:** v0.10
| **Version of CHAOS:** CHAOS-7.11 (0711)

Features
^^^^^^^^
* Updated RC-index file to RC_1997-2022_June_v3.

Version 0.9
-----------
| **Date:** April 1, 2022
| **Release:** v0.9
| **Version of CHAOS:** CHAOS-7.10 (0710)

Features
^^^^^^^^
* Updated RC-index file to RC_1997-2022_Feb_v3.
* Changed the default leap year setting when loading/saving shc-files using
  the model classes to ``leap_year=False``.
* Added function :func:`chaosmagpy.chaos.load_CALS7K_txtfile` to read the
  CALS7K coefficients file.
* Function :func:`chaosmagpy.model_utils.design_gauss` now accepts
  multidimensional shapes of input grids and preserves them in the output.
* Added new method :meth:`chaosmagpy.chaos.Base.to_ppdict`, which returns a
  dictionary of the pp-form compatible with MATLAB.
* Added support for calibration parameters.
* Renamed "params.version" in basicConfig to "params.CHAOS_version".

Bugfixes
^^^^^^^^
* Functions :func:`chaosmagpy.data_utils.dyear_to_mjd` and
  :func:`chaosmagpy.data_utils.mjd_to_dyear` now correctly convert
  negative decimal years and negative modified Julian dates (erroneous offset
  of 1 day due to rounding to integer values).

Version 0.8
-----------
| **Date:** December 9, 2021
| **Release:** v0.8
| **Version of CHAOS:** CHAOS-7.9 (0709)

Features
^^^^^^^^
* Updated RC-index file to RC_1997-2021_November_v3.
* Added ability to compute field components at the geographic poles.
* Removed cdot from SV, SA units in :func:`chaosmagpy.data_utils.gauss_units`.
* Added :func:`chaosmagpy.coordinate_utils.sh_analysis`, which performs a
  spherical harmonic expansion on a callable.

Bugfixes
^^^^^^^^
* Removed Euler pre-rotation, which was not correctly implemented, and added
  a warning.
* Fixed shc-file loader to correctly exclude extrapolation sites.
* Fixed numpy broadcasting error in :func:`chaosmagpy.data_utils.mjd2000`.

Version 0.7.1
-------------
| **Date:** August 05, 2021
| **Release:** v0.7.1
| **Version of CHAOS:** CHAOS-7.8 (0708)

Bugfixes
^^^^^^^^
* Fixed CHAOS shc-file loader.

Version 0.7
-----------
| **Date:** August 05, 2021
| **Release:** v0.7
| **Version of CHAOS:** CHAOS-7.8 (0708)

Features
^^^^^^^^
* Added matplotlib's plot_directive for sphinx and added more examples to a
  new gallery section in the documentation.
* Added :func:`chaosmagpy.model_utils.pp_from_bspline` to convert the spline
  coefficients from B-spline to PP format.
* Changed the way piecewise polynomials are produced from the coefficients in
  shc-files. A B-spline representation is now created in an intermediate step
  to ensure coefficient time series that are smooth.
* Changed the number format to ``'16.8f'`` when writing shc-files to increase
  precision.
* Configuration parameters in ``chaosmagpy.basicConfig`` are now saved to and
  loaded from a json-formatted txt-file.
* Added keyword arguments to :meth:`chaosmagpy.chaos.CHAOS.synth_coeffs_sm`
  and :meth:`chaosmagpy.chaos.CHAOS.synth_values_sm` to provide the RC-index
  values directly instead of using the built-in RC-index file.

Version 0.6
-----------
| **Date:** March 22, 2021
| **Release:** v0.6
| **Version of CHAOS:** CHAOS-7.6 (0706), CHAOS-7.7 (0707)

News
^^^^
The latest version of CHAOS (CHAOS-7.7) corrects an error in the distributed
CHAOS-7.6 model files. The mat-file and shc-file for CHAOS-7.6 were due to a
bug identical to CHAOS-7.5, i.e. not correctly updated. The distributed spline
coefficient file for CHAOS-7.6 was correct. The CHAOS-7.7 release corrects the
errors and all CHAOS-7.7 files use updated data to March 2021.

ChaosMagPy v0.6 also works with CHAOS-7.7 and does not need to be
updated (2021-06-15).

Features
^^^^^^^^
* Added new usage sections to the documentation

Bugfixes
^^^^^^^^
* Fixed broken link to RC-index file (GitHub issue #5).
* Added lxml to installation instructions
  (needed for webpage requests, optional).
* Require hdf5storage version 0.1.17 (fixed read/write intent)

Version 0.5
-----------
| **Date:** December 23, 2020
| **Release:** v0.5
| **Version of CHAOS:** CHAOS-7.5 (0705)

Features
^^^^^^^^
* Modified "nio" colormap to be white-centered.
* Added spatial power spectrum of toroidal sources
  (:func:`chaosmagpy.model_utils.power_spectrum`)

Version 0.4
-----------
| **Date:** September 10, 2020
| **Release:** v0.4
| **Version of CHAOS:** CHAOS-7.3 (0703), CHAOS-7.4 (0704)

Features
^^^^^^^^
* Updated RC-index file to RC_1997-2020_Aug_v4.dat.
* Model name defaults to the filename it was loaded from.
* Added function to read the COV-OBS.x2 model
  (:func:`chaosmagpy.chaos.load_CovObs_txtfile`) from a text file.
* Added function to read the gufm1 model
  (:func:`chaosmagpy.chaos.load_gufm1_txtfile`) from a text file.
* Added class method to initialize :class:`chaosmagpy.chaos.BaseModel` from a
  B-spline representation.

Version 0.3
-----------
| **Date:** April 20, 2020
| **Release:** v0.3
| **Version of CHAOS:** CHAOS-7.2 (0702)

News
^^^^
The version identifier of the CHAOS model using ``x``, which stands for an
extension of the model, has been replaced in favor of a simple version
numbering. For example, ``CHAOS-6.x9`` is the 9th extension of the CHAOS-6
series. But starting with the release of the CHAOS-7 series, the format
``CHAOS-7.1`` has been adopted to indicate the first release of the series,
``CHAOS-7.2`` the second release (formerly the first extension) and so on.

Features
^^^^^^^^
* Updated RC-index file to RC_1997-2020_Feb_v4.dat.
* Removed version keyword of :class:`chaosmagpy.chaos.CHAOS` to avoid
  confusion.
* Added ``verbose`` keyword to the ``call`` method of
  :class:`chaosmagpy.chaos.CHAOS` class to avoid printing messages.
* Added :func:`chaosmagpy.data_utils.timestamp` function to convert modified
  Julian date to NumPy's datetime format.
* Added more examples to the :class:`chaosmagpy.chaos.CHAOS` methods.
* Added optional ``nmin`` and ``mmax`` to
  :func:`chaosmagpy.model_utils.design_gauss` and
  :func:`chaosmagpy.model_utils.synth_values` (nmin has been redefined).
* Added optional derivative to :func:`chaosmagpy.model_utils.colloc_matrix`
  of the B-Spline collocation.
  New implementation does not have the missing endpoint problem.
* Added ``satellite`` keyword to change default satellite names when loading
  CHAOS mat-file.

Version 0.2.1
-------------
| **Date:** November 20, 2019
| **Release:** v0.2.1
| **Version of CHAOS:** CHAOS-7.1 (0701)

Bugfixes
^^^^^^^^
* Corrected function :func:`chaosmagpy.coordinate_utils.zenith_angle` which was
  computing the solar zenith angle from ``phi`` defined as the hour angle and
  NOT the geographic longitude. The hour angle is measure positive towards West
  and negative towards East.

Version 0.2
-----------
| **Date:** October 3, 2019
| **Release:** v0.2
| **Version of CHAOS:** CHAOS-7.1 (0701)

Features
^^^^^^^^
* Updated RC-index file to recent version (August 2019, v6)
* Added option ``nmin`` to :func:`chaosmagpy.model_utils.synth_values`.
* Vectorized :func:`chaosmagpy.data_utils.mjd2000`,
  :func:`chaosmagpy.data_utils.mjd_to_dyear` and
  :func:`chaosmagpy.data_utils.dyear_to_mjd`.
* New function :func:`chaosmagpy.coordinate_utils.local_time` for a simple
  computation of the local time.
* New function :func:`chaosmagpy.coordinate_utils.zenith_angle` for computing
  the solar zenith angle.
* New function :func:`chaosmagpy.coordinate_utils.gg_to_geo` and
  :func:`chaosmagpy.coordinate_utils.geo_to_gg` for transforming geodetic and
  geocentric coordinates.
* Added keyword ``start_date`` to
  :func:`chaosmagpy.coordinate_utils.rotate_gauss_fft`
* Improved performance of :meth:`chaosmagpy.chaos.CHAOS.synth_coeffs_sm` and
  :meth:`chaosmagpy.chaos.CHAOS.synth_coeffs_gsm`.
* Automatically import :func:`chaosmagpy.model_utils.synth_values`.

Deprecations
^^^^^^^^^^^^
* Rewrote :func:`chaosmagpy.data_utils.load_matfile`: now traverses matfile
  and outputs dictionary.
* Removed ``breaks_euler`` and ``coeffs_euler`` from
  :class:`chaosmagpy.chaos.CHAOS` class
  attributes. Euler angles are now handled as :class:`chaosmagpy.chaos.Base`
  class instance.

Bugfixes
^^^^^^^^
* Fixed collocation matrix for unordered collocation sites. Endpoint now
  correctly taken into account.

Version 0.1
-----------
| **Date:** May 10, 2019
| **Release:** v0.1
| **Version of CHAOS:** CHAOS-6-x9

Features
^^^^^^^^
* New CHAOS class method :meth:`chaosmagpy.chaos.CHAOS.synth_euler_angles` to
  compute Euler angles for the satellites from the CHAOS model (used to rotate
  vectors from magnetometer frame to the satellite frame).
* Added CHAOS class methods :meth:`chaosmagpy.chaos.CHAOS.synth_values_tdep`,
  :meth:`chaosmagpy.chaos.CHAOS.synth_values_static`,
  :meth:`chaosmagpy.chaos.CHAOS.synth_values_gsm` and
  :meth:`chaosmagpy.chaos.CHAOS.synth_values_sm` for field value computation.
* RC index file now stored in HDF5 format.
* Filepaths and other parameters are now handled by a configuration dictionary
  called ``chaosmagpy.basicConfig``.
* Added extrapolation keyword to the BaseModel class
  :meth:`chaosmagpy.chaos.Base.synth_coeffs`, linear by default.
* :func:`chaosmagpy.data_utils.mjd2000` now also accepts datetime class
  instances.
* :func:`chaosmagpy.data_utils.load_RC_datfile` downloads latest RC-index file
  from the website if no file is given.

Bugfixes
^^^^^^^^
* Resolved issue in :func:`chaosmagpy.model_utils.degree_correlation`.
* Changed the date conversion to include hours and seconds not just the day
  when plotting the timeseries.

Version 0.1a3
-------------
| **Date:** February 19, 2019
| **Release:** v0.1a3

Features
^^^^^^^^
* New CHAOS class method :meth:`chaosmagpy.chaos.CHAOS.save_matfile` to output
  MATLAB compatible files of the CHAOS model (using the ``hdf5storage``
  package).
* Added ``epoch`` keyword to basevector input arguments of GSM, SM and MAG
  coordinate systems.

Bugfixes
^^^^^^^^
* Fixed problem of the setup configuration for ``pip`` which caused importing
  the package to fail although installation was indicated as successful.

Version 0.1a2
-------------
| **Date:** January 26, 2019
| **Release:** v0.1a2

Features
^^^^^^^^
* :func:`chaosmagpy.data_utils.mjd_to_dyear` and
  :func:`chaosmagpy.data_utils.dyear_to_mjd` convert time with microseconds
  precision to prevent round-off errors in seconds.
* Time conversion now uses built-in ``calendar`` module to identify leap year.

Bugfixes
^^^^^^^^
* Fixed wrong package requirement that caused the installation of
  ChaosMagPy v0.1a1 to fail with ``pip``. If installation of v0.1a1 is needed,
  use ``pip install --no-deps chaosmagpy==0.1a1`` to ignore faulty
  requirements.

Version 0.1a1
-------------
| **Date:** January 5, 2019
| **Release:** v0.1a1

Features
^^^^^^^^
* Package now supports Matplotlib v3 and Cartopy v0.17.
* Loading shc-file now converts decimal year to ``mjd2000`` taking leap years
  into account by default.
* Moved ``mjd2000`` from ``coordinate_utils`` to ``data_utils``.
* Added function to compute degree correlation.
* Added functions to compute and plot the power spectrum.
* Added flexibility to the function synth_values: now supports NumPy
  broadcasting rules.
* Fixed CHAOS class method synth_coeffs_sm default source parameter: now
  defaults to ``'external'``.

Deprecations
^^^^^^^^^^^^
* Optional argument ``source`` when saving shc-file has been renamed to
  ``model``.
* ``plot_external_map`` has been renamed to ``plot_maps_external``
* ``synth_sm_field`` has been renamed to ``synth_coeffs_sm``
* ``synth_gsm_field`` has been renamed to ``synth_coeffs_gsm``
* ``plot_static_map`` has been renamed to ``plot_maps_static``
* ``synth_static_field`` has been renamed to ``synth_coeffs_static``
* ``plot_tdep_maps`` has been renamed to ``plot_maps_tdep``
* ``synth_tdep_field`` has been renamed to ``synth_coeffs_tdep``

Version 0.1a0
-------------
| **Date:** October 13, 2018
| **Release:** v0.1a0

Initial release to the users for testing.
