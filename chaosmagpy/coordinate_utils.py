# Copyright (C) 2025 Clemens Kloss
#
# This file is part of ChaosMagPy.
#
# ChaosMagPy is released under the MIT license. See LICENSE in the root of the
# repository for full licensing details.

"""
`chaosmagpy.coordinate_utils` provides functions related to coordinate
transformations. Typical coordinate reference frames and corresponding
abbreviations are listed in the following.

**Abbreviations**

GEO : Geographic coordinate system (orthogonal)
    Geocentric coordinate system with the z-axis along Earth's rotation axis,
    x-axis pointing to Greenwich and y-axis completing the right-handed system.
    This is also referred to as the ECEF (Earth-centered Earth-fixed)
    coordinate system.
GG : Geodetic coordinate system (orthogonal).
    Earth is approximated by a spheroid (ellipsoid of revolution) with
    equatorial radius `a` and polar radius `b`, `b < a`. The numerical values
    of these radii are defined by the World Geodetic System 1984 (WGS84).
USE : Local Up-South-East frame defined on the sphere.
    Axes directions are defined as Up-South-East at the point of interest on
    the sphere (e.g., B_radius, B_theta, B_phi, the spherical components of
    GEO).
GSM : Geocentric Solar Magnetospheric coordinate system (orthogonal).
    With x-axis pointing towards the sun, y-axis perpendicular to plane spanned
    by Earth-Sun line and the dipole axis, z-axis completes right-handed
    system.
SM : Solar Magnetic coordinate system (orthogonal)
    With z-axis along dipole axis pointing to the geomagnetic north pole,
    y-axis perpendicular to plane containing the dipole axis and the Earth-Sun
    line, x-axis completes the right-handed system.
MAG : Magnetic coordinate system (centered dipole, orthogonal)
    With z-axis pointing to the geomagnetic north pole, x-axis in the plane
    spanned by the dipole axis and Earth's rotation axis, and y-axis completing
    the right-handed system.

.. autosummary::
    :toctree: functions

    igrf_dipole
    dipole_to_vec
    dipole_tilt
    clock_angle
    coupling_Newell
    synth_rotate_gauss
    rotate_gauss_fft
    rotate_gauss
    sh_analysis
    sun_position
    zenith_angle
    spherical_to_cartesian
    cartesian_to_spherical
    basevectors_gg
    basevectors_gsm
    basevectors_sm
    basevectors_use
    basevectors_mag
    geo_to_gg
    gg_to_geo
    geo_to_base
    matrix_geo_to_base
    transform_points
    transform_vectors
    qdipole
    center_azimuth
    local_time
    q_response
    q_response_1D

"""

import numpy as np
import os
from math import factorial
from . import model_utils
from . import config_utils
from . import data_utils

try:
    import apexpy
except ImportError:
    HAS_APX = False
else:
    HAS_APX = True


ROOT = os.path.abspath(os.path.dirname(__file__))


def igrf_dipole(epoch=None):
    """
    Compute unit vector that is anti-parallel to the IGRF dipole.

    The vector points towards the geomagnetic north pole (located in the
    Northern Hemisphere).

    Parameters
    ----------
    epoch : {'2015', '2020', '2010'}, optional
        Epoch of IGRF-12 (2015), IGRF-13 (2020), and IGRF-11 (2010).
        Epoch `"2015"` of IGRF-12 is used by default.

    Returns
    -------
    dipole : ndarray, shape (3,)
        Unit vector pointing to geomagnetic north pole (located in Northern
        Hemisphere).

    """

    # default IGRF dipole
    epoch = '2015' if epoch is None else str(epoch)

    if epoch == '2015':
        # IGRF-12 dipole coefficients, epoch 2015: theta = 9.69, phi = 287.37
        dipole = _dipole_to_unit(np.array([-29442.0, -1501.0, 4797.1]))

    elif epoch == '2020':
        # IGRF-13 dipole coefficients, epoch 2020
        dipole = _dipole_to_unit(np.array([-29404.8, -1450.9, 4652.5]))

    elif epoch == '2010':
        # dipole as used in original chaos software (IGRF-11), epoch 2010
        dipole = _dipole_to_unit(11.32, 289.59)

    else:
        raise ValueError('Only epoch "2010" (IGRF-11), '
                         '"2015" (IGRF-12), and "2020" '
                         '(IGRF-13) are supported.')

    return dipole


def _dipole_to_unit(*args):
    """
    Convert degree-1 SH coefficients or geomagnetic north pole positions to
    unit vectors.

    Parameters
    ----------
    *args : ndarray, shapes (...) or (..., 3)
        Takes as input either two arrays ``theta``, ``phi`` in degrees, or a
        single array where the trailing dimension contains
        ``[g10, g11, h11]``, or three arrays ``g10``, ``g11``, ``h11``
        (in that order). All arrays must broadcast.

    Returns
    -------
    vector : ndarray, shape (..., 3)
        Unit vectors pointing to the geomagnetic north pole.

    """

    if len(args) == 1:
        vector = np.roll(args[0], shift=-1, axis=-1)  # g11, h11, g10: dipole

        # unit vector, opposite to dipole
        vector = -vector / np.linalg.norm(vector, axis=-1, keepdims=True)

    elif len(args) == 2:
        theta = np.radians(args[0])
        phi = np.radians(args[1])

        vector = np.stack([np.sin(theta)*np.cos(phi),
                           np.sin(theta)*np.sin(phi),
                           np.cos(theta)], axis=-1)

    elif len(args) == 3:
        # g11, h11, g10: dipole
        vector = np.stack([args[1], args[2], args[0]], axis=-1)

        # unit vector, opposite to dipole
        vector = -vector / np.linalg.norm(vector, axis=-1, keepdims=True)

    else:
        raise ValueError('Only 1, 2 or 3 inputs accepted '
                         f'but {len(args)} given.')

    return vector


def dipole_to_vec(dipole=None):
    """
    Convert degree-1 SH coefficients or geomagnetic north pole positions to
    unit vectors.

    Parameters
    ----------
    dipole : ndarray, shape (..., 3), or tuple of ndarrays, optional
        Dipole coefficients. Accepted input is a single array with the dipole
        coefficients :math:`g_1^0`, :math:`g_1^1` and :math:`h_1^1` in the
        trailing dimension; or a tuple of two arrays, where the first array is
        the co-latitude of the geomagentic north pole and the second is its
        longitude; or a tuple of three arrays, one array for each dipole
        coefficient in the natural order. Defaults to the SH coefficients in
        ``basicConfig['params.dipole']``.

    Returns
    -------
    vec : ndarray, shape (..., 3)
        Unit vector pointing in the direction of the geomagnetic north pole.

    """

    if dipole is None:
        # take [g10, g11, h11]-format in the config dictionary
        vec = _dipole_to_unit(config_utils.basicConfig['params.dipole'])
    elif isinstance(dipole, (tuple, list)):
        # unpack: accepts either two arrays (theta_np and phi_np), or
        # three arrays (one for each coefficient: g10, g11, h11)
        vec = _dipole_to_unit(*dipole)
    else:
        # single array with [g10, g11, h11] in the trailing dimension
        vec = _dipole_to_unit(dipole)

    return vec


def dipole_tilt(time):
    """
    Compute the dipole tilt angle in degrees.

    Parameters
    ----------
    time : ndarray, shape (...)
        Time in modified Julian date.

    Returns
    -------
    tilt : ndarray, shape (...)
        Dipole tilt angle in degrees.

    """

    s = sun_position(time)  # theta and phi position
    s = np.stack(spherical_to_cartesian(1., s[0], s[1]), axis=-1)

    m = igrf_dipole()

    return np.degrees(np.arcsin(np.matmul(s, m)))


def clock_angle(By, Bz):
    """
    Compute the interplanetary magnetic field clock angle in degrees.

    Parameters
    ----------
    By : ndarray, shape (...)
        Y-component of the IMF in GSM coordinates.
    Bz : ndarray, shape (...)
        Z-component of the IMF in GSM coordinates.

    Returns
    -------
    ca : ndarray, shape (...)
        Clock angle in degrees.

    """

    return np.degrees(np.arctan2(By, Bz))


def coupling_Newell(By, Bz, Vx):
    """
    Compute Newell's coupling function from solar wind parameters.

    Parameters
    ----------
    By : ndarray, shape (...)
        Y-component of the IMF in GSM coordinates (nT).
    Bz : ndarray, shape (...)
        Z-component of the IMF in GSM coordinates (nT).
    Vx : ndarray, shape (...)
        X-component of the solar wind in GSM/GSE coordinates (km/s).

    Returns
    -------
    Eps : ndarray, shape (...)
        Newell's coupling function.
    Tau : ndarray, shape (...)
        Measure that maximizes for northward IMF.

    Notes
    -----
    Newell's coupling function is proportional to the rate at which magnetic
    flux is openend on the dayside of the magnetopause through reconnection.

    The original definition of the coupling function only differs in the
    factor :math:`10^{-3}`, which is included in the definition used here:

    .. math::

        \\epsilon &= 10^{-3} \\mathit{V_x}^{4/3} B_T^{2/3}
            \\sin\\left(\\frac{|\\theta_c|}{2}\\right)^{8/3} \\\\
        \\tau &= 10^{-3} \\mathit{V_x}^{4/3} B_T^{2/3}
            \\cos\\left(\\frac{|\\theta_c|}{2}\\right)^{8/3}

    where :math:`V_x` is the solar wind speed in km/s, :math:`\\theta_c` is the
    clock angle and :math:`B_T` the IMF strength in the y-z-plane of the GSM
    coordinate system in nT.

    """

    B = np.sqrt(By**2 + Bz**2)
    ca = np.radians(clock_angle(By, Bz))

    epsilon = np.abs(Vx)**(4./3) * B**(2./3) * np.abs(np.sin(ca/2))**(8./3)
    tau = np.abs(Vx)**(4./3) * B**(2./3) * np.cos(ca/2)**(8./3)

    return epsilon/1e3, tau/1e3


def synth_rotate_gauss(time, frequency, spectrum, scaled=None):
    """
    Compute time-dependent matrices that transform spherical harmonic expansion
    from the given Fourier coefficients.

    The function computes matrices that transform the spherical harmonic
    expansion of a time-dependent reference system (e.g. GSM, SM) to GEO using
    Fourier expansion of the transformation coefficients.

    Parameters
    ----------
    time : ndarray, shape (...)
        Time given as modified Julian date, i.e. with respect to the date 0h00
        January 1, 2000 (mjd2000).
    frequency : ndarray, shape (k,) or (k, m, n)
        Vector of positive frequencies given in oscillations per day.
    spectrum : ndarray, shape (k, m, n)
        Fourier components of the matrices (reside in the last two dimensions).
    scaled : bool, optional (defaults to ``False``)
        If ``True``, the function expects `scaled` Fourier coefficients, i.e.
        the non-bias term (all non-zero frequency terms) have been multiplied
        by a factor of 2. Hence, taking the real part of the spectrum
        multiplied with the complex exponentials results in the correctly
        scaled and time-shifted real-valued harmonics.

    Returns
    -------
    matrix : ndarray, shape (..., m, n)

    """

    if scaled is None:
        scaled = False

    time = np.array(time[..., None, None, None], dtype=float)
    frequency = 2*np.pi*np.array(frequency, dtype=float)
    if frequency.ndim == 1:
        frequency.reshape(-1, 1, 1)
    spectrum = np.array(spectrum, dtype=complex)

    # output of shape (..., k, n, m)
    freq_t = frequency*time

    # compute complex exponentials
    harmonics = np.empty(freq_t.shape, dtype=complex)
    harmonics = np.cos(freq_t) + 1j*np.sin(freq_t)

    if scaled is False:
        # scale non-offset coefficients by 2 before synthesizing matrices
        harmonics = np.where(frequency > 0.0, 2*harmonics, harmonics)

    matrix = np.sum(spectrum*harmonics, axis=-3)

    return np.real(matrix)


def rotate_gauss_fft(nmax, kmax, *, qfunc=None, step=None, N=None, filter=None,
                     save_to=None, reference=None, scaled=None,
                     start_date=None):
    """
    Compute Fourier coefficients of the timeseries of matrices that transform
    spherical harmonic expansions (degree ``kmax``) from a time-dependent
    reference system (GSM, SM) to GEO (degree ``nmax``).

    Parameters
    ----------
    nmax : int
        Maximum degree of spherical harmonic expansion with respect to the
        geographic reference frame (GEO).
    kmax : int
        Maximum degree of spherical harmonic expansion with respect to the
        rotated reference system.
    qfunc : callable
        Callable ``q = qfunc(freq, k)`` that returns the complex q-response
        ``q`` (ndarray, shape (``N``,)) given a frequency vector ``freq``
        (ndarray, shape (``N``,)) in (1/sec) and the index ``k`` (int) counting
        the Gauss coefficients in natural order, i.e. ``k = 0`` is
        :math:`g_1^0`, ``k = 1`` is :math:`g_1^1`, ``k = 2`` is :math:`h_1^1`
        and so on.
    step : float
        Sample spacing given in hours (default is 1.0 hour).
    N : int, optional
        Number of samples for which to evaluate the FFT (default is
        N = 8*365.25*24 equiv. to 8 years using default sample spacing).
    filter : int, optional
        Set filter length, i.e. number of Fourier coefficients to be saved
        (default is ``int(N/2+1)``).
    save_to : str, optional
        Path and file name to store output in npz-format. Defaults to
        ``False``, i.e. no file is written.
    reference : {'gsm', 'sm'}, optional
        Time-dependent reference system (default is GSM).
    scaled : bool, optional (default is ``False``)
        If ``True``, the function returns `scaled` Fourier coefficients, i.e.
        the non-bias terms (all non-zero frequency terms) are multiplied by a
        factor of 2. Hence, taking the real part of the first half of the
        spectrum multiplied with the complex exponentials results in the
        correctly scaled and time-shifted real-valued harmonics.
    start_date : float, optional (defaults to ``0.0``, i.e. Jan 1, 2000)
        Time point from which to compute the time series of coefficient
        matrices in modified Julian date.

    Returns
    -------
    frequency, spectrum, frequency_ind, spectrum_ind : ndarray, \
shape (``filter``, ``nmax`` (``nmax`` + 2), ``kmax`` (``kmax`` + 2))
        Unsorted vector of positive frequencies in 1/days and complex fourier
        spectrum of rotation matrices to transform spherical
        harmonic expansions.

    Notes
    -----
    If ``save_to=<filepath>``, then an ``*.npz``-file is written with the
    keywords {'frequency', 'spectrum', 'frequency_ind', 'spectrum_ind', ...}
    and all the possible keywords. Among them, ``'dipole'`` means the three
    spherical harmonic coefficients of the dipole set in
    ``basicConfig['params.dipole']``.

    About the discrete Fourier transform (DFT) used here:

    A discrete periodic signal :math:`x[n]` with :math:`n\\in [0, N-1]`
    (period of `N`) is represented in terms of complex-exponentials as

    .. math::

       x[n] = \\sum_{k=0}^{N-1}X[k]w_N^{kn}, \\qquad w_N = \\exp(i 2\\pi/N)

    Here, :math:`X[k]`, :math:`k\\in [0, N-1]` is the Fourier transform of
    :math:`x[n]`. The DFT is defined as:

    .. math::

       X[k] = \\frac{1}{N}\\sum_{n=0}^{N-1}x[n]w_N^{-kn}

    In ``numpy``, this operation is implemented with

    .. code-block:: python

       import numpy as np

       X = np.fft.fft(x) / N

    Finally, if ``save_to`` is given, only half of the Fourier coefficients
    ``X[0:int(N/2)+1]`` (right-exclusive) are saved (or less if ``filter`` is
    specified).

    """

    if reference is None:
        reference = 'gsm'

    if step is None:
        step = 1.0  # sample spacing of one hour

    if N is None:
        N = int(8*365.25*24)  # number of samples
    else:
        N = int(N)

    if filter is None:  # number of significant Fourier components to be saved
        filter = int(N/2 + 1)
    else:
        filter = int(filter)

    if save_to is None:
        save_to = False  # do not write output file

    if scaled is None:
        scaled = False

    if start_date is None:
        start_date = 0.0

    time = np.arange(N) * step / 24. + start_date  # time in days

    # compute base vectors of time-dependent reference system
    if str(reference).lower() == 'gsm':
        base_1, base_2, base_3 = basevectors_gsm(time)
    elif str(reference).lower() == 'sm':
        base_1, base_2, base_3 = basevectors_sm(time)
    else:
        raise ValueError('Reference system must be either "GSM" or "SM".')

    print("Calculating Gauss rotation matrices for {:}".format(
        reference.upper()))

    # compute transformation matrix: reference to geographic system
    matrix_time = rotate_gauss(nmax, kmax, base_1, base_2, base_3)

    # DFT and proper scaling
    spectrum_full = np.fft.fft(matrix_time, axis=0) / N
    spectrum_full = spectrum_full[:int(N/2+1)]  # remove aliases

    # oscillations per second
    frequency_full = (np.arange(int(N/2+1)) / N) / step / 3600

    if qfunc is None:
        # compute q-response and keep in memory
        q = q_response(frequency_full, nmax)

        # now define qfunc here
        def qfunc(freq, k):
            # index of degree in response
            n = np.floor(np.sqrt(k+1)-1).astype(int)
            return q[n]

    # predefine output arrays
    frequency = np.zeros((filter, nmax*(nmax+2), kmax*(kmax+2)))
    frequency_ind = np.zeros((filter, nmax*(nmax+2), kmax*(kmax+2)))
    spectrum = np.zeros((filter, nmax*(nmax+2), kmax*(kmax+2)),
                        dtype=complex)
    spectrum_ind = np.zeros((filter, nmax*(nmax+2), kmax*(kmax+2)),
                            dtype=complex)

    for k in range(nmax*(nmax+2)):

        # compute Q-response for freqencies and given Gauss coefficient
        response = qfunc(frequency_full, k)

        for ll in range(kmax*(kmax+2)):
            # select specific Fourier coefficients from the rotation matrix
            element = spectrum_full[:, k, ll]

            # modify Fourier components with Q-response
            element_ind = response*element

            # index of sorted element spectrum (descending order)
            sort = np.argsort(np.abs(element))[::-1]
            sort = sort[:filter]  # only keep small number of components

            # index of sorted element spectrum (descending order)
            sort_ind = np.argsort(np.abs(element_ind))[::-1]
            sort_ind = sort_ind[:filter]  # only keep small number

            # write sorted frequency (per day) and fourier components to array
            frequency[:, k, ll] = frequency_full[sort] * (24*3600)
            frequency_ind[:, k, ll] = frequency_full[sort_ind] * (24*3600)
            spectrum[:, k, ll] = element[sort]
            spectrum_ind[:, k, ll] = element_ind[sort_ind]

    if scaled:
        # scale non-offset coefficients by 2
        spectrum = np.where(frequency == 0.0, spectrum, 2*spectrum)
        spectrum_ind = np.where(frequency_ind == 0.0, spectrum_ind,
                                2*spectrum_ind)

    # save several arrays to binary
    if save_to:
        np.savez(str(save_to),
                 frequency=frequency, spectrum=spectrum,
                 frequency_ind=frequency_ind, spectrum_ind=spectrum_ind,
                 step=step, N=N, filter=filter, reference=reference,
                 scaled=scaled,
                 dipole=config_utils.basicConfig['params.dipole'],
                 start_date=start_date)
        print("Output saved to {:}".format(save_to))

    return frequency, spectrum, frequency_ind, spectrum_ind


def rotate_gauss(nmax, kmax, base_1, base_2, base_3):
    """
    Compute matrices for the coordinate transformation of spherical harmonic
    expansions.

    Transform the spherical harmonic expansion in terms of rotated geocentric
    spherical coordinates (e.g. GSM) to the spherical harmonic expansion
    in terms of the standard geographic coordinate system (GEO). The rotated
    coordinate system is described by 3 orthogonal base vectors with components
    in GEO coordinates.

    Parameters
    ----------
    nmax : int
        Maximum degree of spherical harmonic expansion with respect to
        geographic reference (target reference system).
    kmax : int
        Maximum degree of spherical harmonic expansion with respect to rotated
        reference system.
    base_1, base_2, base_3 : ndarray, shape (..., 3)
        Base vectors of rotated reference system given in terms of the
        target reference system. Vectors reside in the last dimension. The base
        vectors are needed for the coordinate transformation.

    Returns
    -------
    matrix : ndarray, shape (..., ``nmax`` (``nmax`` + 2), ``kmax`` \
(``kmax`` + 2))
        Matrices reside in last two dimensions. They transform spherical
        harmonic coefficients of rotated reference (e.g. GSM) to standard
        geographic reference (GEO):

        [g10 g11 h11 ...]_geo = M * [g10 g11 h11 ...]_gsm

    """

    assert (base_1.shape == base_2.shape) and (base_1.shape == base_3.shape)
    time_shape = base_1.shape[:-1]  # retain original shape of grid

    # predefine output array
    matrix_time = np.empty(time_shape + (nmax**2+2*nmax, kmax**2+2*kmax))

    # define Gauss-Legendre grid for surface integration
    n_theta = int((nmax + kmax + 1)/2) + 1  # number of points in colatitude
    n_phi = 2*n_theta  # number of points in azimuth

    # integrates polynomials of degree 2*n_theta-1 exactly
    x, weights = np.polynomial.legendre.leggauss(n_theta)
    theta = np.degrees(np.arccos(x))
    phi = np.arange(n_phi) * np.degrees(2*np.pi)/n_phi

    # compute Schmidt quasi-normalized associated Legendre functions and
    # corresponding normalization
    Pnm = model_utils.legendre_poly(nmax, theta)
    n_Pnm = int((nmax**2+3*nmax)/2)
    norm = np.empty((n_Pnm,))
    for n in range(1, nmax+1):
        lower = int((n**2+n)/2-1)
        upper = int((n**2+3*n)/2)
        norm[lower] = 2/(2*n+1)  # inner product of Pn0
        norm[lower+1:upper] = 4/(2*n+1)  # inner product of Pnm m>0

    # generate grid of rotated reference system
    phi_grid, theta_grid = np.meshgrid(phi, theta)

    # run over time index and produce matrix for every point in time
    for index in np.ndindex(time_shape):

        # predefine array size for each point in time
        matrix = np.empty((nmax*(nmax+2), kmax*(kmax+2)))

        theta_ref, phi_ref = geo_to_base(
            theta_grid, phi_grid, base_1[index], base_2[index], base_3[index])

        # compute Schmidt quasi-normalized associated Legendre functions on
        # grid in rotated reference system: theta_ref, phi_ref
        Pnm_ref = model_utils.legendre_poly(kmax, theta_ref)

        # compute powers of complex exponentials
        nphi_ref = np.radians(np.multiply.outer(np.arange(kmax+1), phi_ref))
        exp_ref = np.cos(nphi_ref) + 1j*np.sin(nphi_ref)

        # loop over columns of matrix
        col = 0  # index of column
        for k in range(1, kmax+1):

            # l = 0
            sh_ref = Pnm_ref[k, 0]*exp_ref[0]  # cplx spherical harmonic
            fft_c = np.fft.fft(sh_ref.real) / n_phi  # only real part non-zero

            # SH analysis: write column of matrix, row by row
            row = 0  # index of row
            for n in range(1, nmax+1):

                lower = int((n**2+n)/2-1)  # index for Pnm norm

                #  m = 0: colatitude integration using Gauss weights
                coeff = np.sum(fft_c[:, 0]*Pnm[n, 0]*weights) / norm[lower]
                matrix[row, col] = coeff.real
                row += 1

                # m > 0
                for m in range(1, n+1):
                    coeff = (np.sum(2*fft_c[:, m]*Pnm[n, m]*weights) /
                             norm[lower+m])
                    matrix[row, col] = coeff.real
                    matrix[row+1, col] = -coeff.imag
                    row += 2

            col += 1  # update index of column

            # l > 0
            for ll in range(1, k+1):
                sh_ref = Pnm_ref[k, ll]*exp_ref[ll]
                fft_c = np.fft.fft(sh_ref.real) / n_phi
                fft_s = np.fft.fft(sh_ref.imag) / n_phi

                # SH analysis: write column of R, row by row
                row = 0  # index of row
                for n in range(1, nmax+1):

                    lower = int((n**2+n) / 2-1)  # index for Pnm norm

                    # cosine part
                    coeff = np.sum(fft_c[:, 0]*Pnm[n, 0]*weights)/norm[lower]
                    matrix[row, col] = coeff.real

                    # sine part
                    coeff = np.sum(fft_s[:, 0]*Pnm[n, 0]*weights)/norm[lower]
                    matrix[row, col+1] = coeff.real

                    row += 1  # update row index

                    # m > 0
                    for m in range(1, n+1):
                        # cosine part
                        coeff = (np.sum(2*fft_c[:, m]*Pnm[n, m]*weights) /
                                 norm[lower+m])
                        matrix[row, col] = coeff.real
                        matrix[row+1, col] = -coeff.imag

                        # sine part
                        coeff = (np.sum(2*fft_s[:, m]*Pnm[n, m]*weights) /
                                 norm[lower+m])
                        matrix[row, col+1] = coeff.real
                        matrix[row+1, col+1] = -coeff.imag

                        row += 2  # update row index

                col += 2  # update column index

        matrix_time[index] = matrix  # write rotation matrix into output

    return matrix_time


def sh_analysis(func, nmax, kmax=None):
    """
    Perform a spherical harmonic expansion of a function defined on a
    spherical surface.

    Parameters
    ----------
    func: callable
        Function takes two inputs: colatitude in degrees and longitude in
        degrees. The function must accept 2-D arrays and preserve shapes.
    nmax: int
        Maximum spherical harmonic degree of the expansion.
    kmax: int, optional, greater than or equal to nmax
        Maximum spherical harmonic degree needed to resolve the output of
        ``func``. This basically increases the number of grid points, which
        improves the accuracy of the numerical integration
        (defaults to ``nmax``). Ignored if ``kmax < nmax``.

    Returns
    -------
    coeffs: ndarray, shape (nmax*(nmax+2),)
        Coefficients of the spherical harmonic expansion.

    Examples
    --------
    First, a straight forward example using the spherical harmonic
    :math:`Y_1^1`:

    >>> import chaosmagpy as cp
    >>> import numpy as np
    >>> #
    >>> def func(theta, phi):
    >>>     n, m = 1, 1
    >>>     Pnm = cp.model_utils.legendre_poly(n, theta)
    >>>     if m >= 0:
    >>>         return np.cos(m*np.radians(phi))*Pnm[n, m]
    >>>     else:
    >>>         return np.sin(abs(m)*np.radians(phi))*Pnm[n, abs(m)]

    >>> cp.coordinate_utils.sh_analysis(func, nmax=1)
        array([0.0000000e+00, 1.0000000e+00, 1.2246468e-16])

    Next, an example with an insufficient number of grid points, which leads to
    inaccurate numerical integration:

    >>> def func(theta, phi):
    >>>     n, m = 7, 0  # increased degree to n=7
    >>>     Pnm = cp.model_utils.legendre_poly(n, theta)
    >>>     return Pnm[n, m]

    >>> cp.coordinate_utils.sh_analysis(func, nmax=1)
        array([0.55555556, 0.00000000e+00, 0.00000000e+00])  # g10 is wrong

    But, by setting ``kmax=7`` and, thus, increasing the number of grid points:

    >>> cp.coordinate_utils.sh_analysis(func, nmax=1, kmax=7)
        array([-1.14491749e-16, 0.00000000e+00, -0.00000000e+00])

    """

    kmax = nmax if kmax is None else int(kmax)

    # define Gauss-Legendre grid for surface integration,
    # quadrature integrates polynomials of degree (2*n_theta - 1) exactly,
    # here the integrands are Pnm(x)*Pkl(x), hence of degree = 2nmax
    n_theta = max(nmax, kmax) + 1  # number of points in colatitude
    n_phi = 2*n_theta  # number of points in azimuth

    x, weights = np.polynomial.legendre.leggauss(n_theta)
    theta = np.degrees(np.arccos(x))
    phi = np.arange(n_phi) * np.degrees(2*np.pi)/n_phi

    # compute Schmidt quasi-normalized associated Legendre functions
    Pnm = model_utils.legendre_poly(nmax, theta)

    # generate surface grid: [0., 360.] x [0., 180.]
    theta_grid, phi_grid = np.meshgrid(theta, phi)

    # predefine array
    coeffs = np.zeros((nmax*(nmax+2),), dtype=float)

    # evaluate function at grid points
    F = func(theta_grid, phi_grid)

    fft = np.fft.fft(F, axis=0) / n_phi

    row = 0  # index of row
    for n in range(1, nmax+1):

        norm = 2. / (2*n + 1)  # inner product of Pnm's

        # m = 0
        c = np.sum(fft[0]*Pnm[n, 0]*weights) / norm
        coeffs[row] = c.real
        row += 1

        # m > 0
        for m in range(1, n+1):

            c = np.sum(fft[m]*Pnm[n, m]*weights) / norm
            coeffs[row] = c.real
            coeffs[row + 1] = -c.imag

            row += 2  # update row index

    return coeffs


def sun_position(time):
    """
    Computes the sun's position in longitude and colatitude at a given time
    (mjd2000).

    It is accurate for years 1901 through 2099, to within 0.006 deg.
    Input shape is preserved.

    Parameters
    ----------
    time : ndarray, shape (...)
        Time given as modified Julian date, i.e. with respect to the date 0h00
        January 1, 2000 (mjd2000).

    Returns
    -------
    theta : ndarray, shape (...)
        Geocentric colatitude of sun's position in degrees
        :math:`[0^\\circ, 180^\\circ]`.
    phi : ndarray, shape (...)
        Longitude (eastward positive) of sun's position in degrees
        :math:`(-180^\\circ, 180^\\circ]`.

    References
    ----------
    Taken from `here <http://jsoc.stanford.edu/doc/keywords/Chris_Russel/
    Geophysical%20Coordinate%20Transformations.htm#appendix2>`_

    """
    rad = np.pi / 180
    year = 2000  # reference year for mjd2000
    assert np.all((year + time // 365.25) < 2099) \
        and np.all((year - time // 365.25) > 1901), \
        ("Time must be between 1901 and 2099.")

    frac_day = np.remainder(time, 1)  # decimal fraction of a day
    julian_date = 365 * (year-1900) + (year-1901)//4 + time + 0.5

    t = julian_date/36525
    v = np.remainder(279.696678 + 0.9856473354*julian_date, 360.)
    g = np.remainder(358.475845 + 0.985600267*julian_date, 360.)

    slong = v + (1.91946 - 0.004789*t)*np.sin(g*rad) + 0.020094*np.sin(2*g*rad)
    obliq = (23.45229 - 0.0130125*t)
    slp = (slong - 0.005686)

    sind = np.sin(obliq*rad)*np.sin(slp*rad)
    cosd = np.sqrt(1.-sind**2)

    #  sun's declination in radians
    declination = np.arctan(sind/cosd)

    # sun's right ascension in radians (0, 2*pi)
    right_ascension = np.pi - np.arctan2(sind/(cosd * np.tan(obliq*rad)),
                                         -np.cos(slp*rad)/cosd)

    # Greenwich mean sidereal time in radians (0, 2*pi)
    gmst = np.remainder(279.690983 + 0.9856473354*julian_date
                        + 360.*frac_day + 180., 360.) * rad

    theta = np.degrees(np.pi/2 - declination)  # convert to colatitude
    phi = center_azimuth(np.degrees(right_ascension - gmst))

    return theta, phi


def zenith_angle(time, theta, phi):
    """
    Compute the solar zenith angle.

    Parameters
    ----------
    time : ndarray, shape (...)
        Time in modified Julian date.
    theta : ndarray, shape (...)
        Colatitude in degrees.
    phi : ndarray, shape (...)
        Longitude in degrees.

    Returns
    -------
    zeta : ndarray, shape (...)
        Zenith angle in degrees :math:`[0^\\circ, 180^\\circ]` (angle between
        the local zenith and the center of the solar disc). Solar elevation
        angle is then computed by :math:`90^\\circ - \\theta_\\mathrm{zenith}`.

    """

    theta_sun, phi_sun = sun_position(time)

    colat = np.radians(theta_sun)
    azim = np.radians(phi_sun)
    theta = np.radians(theta)
    phi = np.radians(phi)

    cos_zeta = (np.cos(theta)*np.cos(colat) +
                np.sin(theta)*np.sin(colat)*np.cos(azim - phi))

    return np.degrees(np.arccos(cos_zeta))


def spherical_to_cartesian(radius, theta, phi):
    """
    Convert spherical coordinates to cartesian coordinates.

    Parameters
    ----------
    radius : float or ndarray, shape (...)
        Radius.
    theta : float or ndarray, shape (...)
        Colatitude in degrees.
    phi : float or ndarray, shape (...)
        Longitude in degrees.

    Returns
    -------
    x, y, z : float or ndarray, shape(...)
        Cartesian coordinates.

    """

    theta, phi = np.radians(theta), np.radians(phi)

    x = np.array(radius) * np.cos(phi) * np.sin(theta)
    y = np.array(radius) * np.sin(phi) * np.sin(theta)
    z = np.array(radius) * np.cos(theta)

    return x, y, z


def cartesian_to_spherical(x, y, z):
    """
    Convert cartesian coordinates to spherical coordinates.

    Parameters
    ----------
    x, y, z : float or ndarray, shape (...)

    Returns
    -------
    radius : float or ndarray, shape (...)
        Radius.
    theta : float or ndarray, shape (...)
        Colatitude in degrees :math:`[0^\\circ, 180^\\circ]`.
    phi : float or ndarray, shape (...)
        Longitude in degrees :math:`(-180^\\circ,180^\\circ]`.
    """

    radius = np.sqrt(x**2 + y**2 + z**2)
    theta = np.arctan2(np.sqrt(x**2 + y**2), z)
    phi = np.arctan2(y, x)

    return radius, np.degrees(theta), np.degrees(phi)


def gg_to_geo(height, beta, X=None, Z=None):
    """
    Compute spherical geographic coordinates and components from geodetic
    coordinates and components as defined by the World Geodetic System 1984
    (WGS84).

    The equatorial and polar radius of the ellipsoid that approximates Earth's
    surface are stored in ``chaosmagpy.basicConfig['params.ellipsoid']``.

    Parameters
    ----------
    height : ndarray, shape (...)
        Altitude in kilometers.
    beta : ndarray, shape (...)
        Geodetic colatitude
    X : ndarray, shape (...), optional
        Geodetic northward vector component.
    Z : ndarray, shape (...), optional
        Geodetic downward vector component.

    Returns
    -------
    radius : ndarray, shape (...)
        Radius in kilometers.
    theta : ndarray, shape (...)
        Geocentric colatitude in degrees.
    B_radius : ndarray, shape (...), optional
        Radially upward vector component (only returned if ``X`` and ``Z``
        are provided).
    B_theta : ndarray, shape (...), optional
        Spherical southward vector component (only returned if ``X`` and ``Z``
        are provided).

    References
    ----------
    The coordinate transformations are taken from Equations (51)-(53) in
    "The main field" (chapter 4) by Langel, R. A. in: "Geomagnetism", Volume 1,
    Jacobs, J. A., Academic Press, 1987. The vector rotation is taken from
    Equation (4) in "5.02 - The Present and Future Geomagnetic Field" by Hulot
    et al. in: Treatise on Geophysics, Elsevier, 2015.

    """

    a = config_utils.basicConfig['params.ellipsoid'][0]  # equatorial radius
    b = config_utils.basicConfig['params.ellipsoid'][1]  # polar radius

    # convert geodetic colatitude to latitude
    alpha = np.radians(90. - beta)

    sin_alpha_2 = np.sin(alpha)**2
    cos_alpha_2 = np.cos(alpha)**2

    factor = height*np.sqrt(a**2*cos_alpha_2 + b**2*sin_alpha_2)
    gamma = np.arctan2((factor + b**2)*np.tan(alpha), (factor + a**2))

    theta = 90. - np.degrees(gamma)
    radius = np.sqrt(height**2 + 2*factor +
                     a**2*(1. - (1. - (b/a)**4)*sin_alpha_2) /
                          (1. - (1. - (b/a)**2)*sin_alpha_2))

    # transform vector components
    if (X is not None) and (Z is not None):

        gg_1, _, gg_3 = basevectors_gg(theta, beta)

        # components of base vectors are the columns of the rotation matrix
        B_radius = gg_1[..., 0]*X + gg_3[..., 0]*Z
        B_theta = gg_1[..., 1]*X + gg_3[..., 1]*Z

        return radius, theta, B_radius, B_theta

    else:
        return radius, theta


def geo_to_gg(radius, theta, B_radius=None, B_theta=None):
    """
    Compute geodetic coordinates and components as defined by the World
    Geodetic System 1984 (WGS84) from spherical geographic coordinates and
    components.

    The equatorial and polar radius of the ellipsoid that approximates Earth's
    surface are stored in ``chaosmagpy.basicConfig['params.ellipsoid']``.

    Parameters
    ----------
    radius : ndarray, shape (...)
        Radius in kilometers.
    theta : ndarray, shape (...)
        Geocentric colatitude in degrees.
    B_radius : ndarray, shape (...), optional
        Radially upward vector component.
    B_theta : ndarray, shape (...), optional
        Spherical southward vector component.

    Returns
    -------
    height : ndarray, shape (...)
        Altitude in kilometers.
    beta : ndarray, shape (...)
        Geodetic colatitude in degrees.
    X : ndarray, shape (...), optional
        Geodetic northward vector component (only returned if ``B_radius`` and
        ``B_theta`` are provided).
    Z : ndarray, shape (...), optional
        Geodetic downward vector component (only returned if ``B_radius`` and
        ``B_theta`` are provided).

    Notes
    -----
    Round-off errors might lead to a failure of the algorithm especially but
    not exclusively for points close to the geographic poles. Corresponding
    geodetic coordinates are returned as NaN.

    References
    ----------
    The function uses Heikkinen's algorithm taken from "Conversion of
    Earth-centered Earth-fixed coordinates to geodetic coordinates" by Zhu, J.
    in: IEEE Transactions on Aerospace and Electronic Systems, 1994, vol. 30,
    num. 3, pp. 957-961. The vector rotation is taken from Equation (4) in
    "5.02 - The Present and Future Geomagnetic Field" by Hulot et al. in:
    Treatise on Geophysics, Elsevier, 2015.

    """

    a = config_utils.basicConfig['params.ellipsoid'][0]  # equatorial radius
    b = config_utils.basicConfig['params.ellipsoid'][1]  # polar radius

    a2 = a**2
    b2 = b**2

    e2 = (a2 - b2) / a2  # squared eccentricity
    e4 = e2*e2
    ep2 = (a2 - b2) / b2  # squared primed eccentricity

    r = radius * np.sin(np.radians(theta))
    z = radius * np.cos(np.radians(theta))

    r2 = r**2
    z2 = z**2

    F = 54*b2*z2

    G = r2 + (1. - e2)*z2 - e2*(a2 - b2)

    c = e4*F*r2 / G**3

    s = (1. + c + np.sqrt(c**2 + 2*c))**(1./3)

    P = F / (3*(s + 1./s + 1.)**2 * G**2)

    Q = np.sqrt(1. + 2*e4*P)

    r0 = -P*e2*r / (1. + Q) + np.sqrt(
        0.5*a2*(1. + 1./Q) - P*(1. - e2)*z2 / (Q*(1. + Q)) - 0.5*P*r2)

    U = np.sqrt((r - e2*r0)**2 + z2)

    V = np.sqrt((r - e2*r0)**2 + (1. - e2)*z2)

    z0 = b2*z/(a*V)

    height = U*(1. - b2 / (a*V))

    beta = 90. - np.degrees(np.arctan2(z + ep2*z0, r))

    # transform vector components
    if (B_radius is not None) and (B_theta is not None):

        gg_1, _, gg_3 = basevectors_gg(theta, beta)

        # components of base vectors are the row of the rotation matrix
        X = gg_1[..., 0]*B_radius + gg_1[..., 1]*B_theta
        Z = gg_3[..., 0]*B_radius + gg_3[..., 1]*B_theta

        return height, beta, X, Z

    else:
        return height, beta


def basevectors_gg(theta, beta):
    """
    Compute the geodetic basevectors of the WGS84.

    Parameters
    ----------
    theta : ndarray, shape (...)
        Geocentric colatitude in degrees.
    beta : ndarray, shape (...)
        Geodetic colatitude in degrees.

    Returns
    -------
    gg_1, gg_2, gg_3 : ndarray, shape (..., 3)
        Geodetic unit base vectors resolved into the spherical components of
        GEO.

    """
    psi = np.radians(theta - beta)  # difference angle

    grid_shape = np.broadcast(theta, beta).shape

    # predefine output, the components of the base vectors in the last
    # dimensions: shape (..., 3, 3)
    gg_1 = np.zeros(grid_shape + (3,))
    gg_2 = np.zeros(grid_shape + (3,))
    gg_3 = np.zeros(grid_shape + (3,))

    gg_1[..., 0] = -np.sin(psi)
    gg_1[..., 1] = -np.cos(psi)

    gg_2[..., 2] = 1.

    gg_3[..., 0] = -np.cos(psi)
    gg_3[..., 1] = np.sin(psi)

    return gg_1, gg_2, gg_3


def basevectors_gsm(time, dipole=None):
    """
    Compute the unit base vectors of the GSM coordinate system.

    Parameters
    ----------
    time : float or ndarray, shape (...)
        Time given as modified Julian date, i.e. with respect to the date 0h00
        January 1, 2000 (mjd2000).
    dipole : ndarray, shape (..., 3), or tuple of ndarrays, optional
        Dipole coefficients. Accepted input is a single array with the dipole
        coefficients :math:`g_1^0`, :math:`g_1^1` and :math:`h_1^1` in the
        trailing dimension; or a tuple of two arrays, where the first array is
        the co-latitude of the geomagentic north pole and the second is its
        longitude; or a tuple of three arrays, one array for each dipole
        coefficient in the natural order. Defaults to the SH coefficients in
        ``basicConfig['params.dipole']``.

    Returns
    -------
    gsm_1, gsm_2, gsm_3 : ndarray, shape (..., 3)
        GSM unit base vectors resolved into the cartesian components of GEO.

    """

    vec = dipole_to_vec(dipole)

    # get sun's position at specified times
    theta_sun, phi_sun = sun_position(time)

    # compute sun's position
    x_sun, y_sun, z_sun = spherical_to_cartesian(1, theta_sun, phi_sun)

    # create array in which the first unit vector resides in last dimension
    gsm_1 = np.empty(x_sun.shape + (3,))
    gsm_1[..., 0] = x_sun
    gsm_1[..., 1] = y_sun
    gsm_1[..., 2] = z_sun

    # compute second base vector of GSM using the cross product of the
    # dipole unit vector with the first unit base vector

    gsm_2 = np.cross(vec, gsm_1)  # over last dimension by default
    norm_gsm_2 = np.linalg.norm(gsm_2, axis=-1, keepdims=True)
    gsm_2 = gsm_2 / norm_gsm_2

    # compute third unit base vector using the cross product of first and
    # second unit base vector
    gsm_3 = np.cross(gsm_1, gsm_2)

    return gsm_1, gsm_2, gsm_3


def basevectors_sm(time, dipole=None):
    """
    Compute the unit base vectors of the SM coordinate system.

    Parameters
    ----------
    time : float or ndarray, shape (...)
        Time given as modified Julian date, i.e. with respect to the date 0h00
        January 1, 2000 (mjd2000).
    dipole : ndarray, shape (..., 3), or tuple of ndarrays, optional
        Dipole coefficients. Accepted input is a single array with the dipole
        coefficients :math:`g_1^0`, :math:`g_1^1` and :math:`h_1^1` in the
        trailing dimension; or a tuple of two arrays, where the first array is
        the co-latitude of the geomagentic north pole and the second is its
        longitude; or a tuple of three arrays, one array for each dipole
        coefficient in the natural order. Defaults to the SH coefficients in
        ``basicConfig['params.dipole']``.

    Returns
    -------
    sm_1, sm_2, sm_3 : ndarray, shape (..., 3)
        SM unit base vectors resolved into the cartesian components of GEO.

    """

    vec = dipole_to_vec(dipole)

    # get sun's position at specified times and convert to cartesian
    theta_sun, phi_sun = sun_position(time)
    x_sun, y_sun, z_sun = spherical_to_cartesian(1, theta_sun, phi_sun)

    # create array in which the sun's vector resides in last dimension
    s = np.empty(x_sun.shape + (3,))
    s[..., 0] = x_sun
    s[..., 1] = y_sun
    s[..., 2] = z_sun

    # set third unit base vector of SM to dipole unit vector
    sm_3 = np.empty(x_sun.shape + (3,))
    sm_3[..., 0] = vec[..., 0]
    sm_3[..., 1] = vec[..., 1]
    sm_3[..., 2] = vec[..., 2]

    # compute second base vector of SM using the cross product of the IGRF
    # dipole unit vector and the sun direction vector
    sm_2 = np.cross(sm_3, s)
    norm_sm_2 = np.linalg.norm(sm_2, axis=-1, keepdims=True)
    sm_2 = sm_2 / norm_sm_2

    # compute third unit base vector using the cross product of second and
    # third unit base vector
    sm_1 = np.cross(sm_2, sm_3)

    return sm_1, sm_2, sm_3


def basevectors_mag(dipole=None):
    """
    Compute the unit base vectors of the centered dipole coordinate system
    (also referred to as MAG).

    Parameters
    ----------
    dipole : ndarray, shape (..., 3), or tuple of ndarrays, optional
        Dipole coefficients. Accepted input is a single array with the dipole
        coefficients :math:`g_1^0`, :math:`g_1^1` and :math:`h_1^1` in the
        trailing dimension; or a tuple of two arrays, where the first array is
        the co-latitude of the geomagentic north pole and the second is its
        longitude; or a tuple of three arrays, one array for each dipole
        coefficient in the natural order. Defaults to the SH coefficients in
        ``basicConfig['params.dipole']``.

    Returns
    -------
    mag_1, mag_2, mag_3 : ndarray, shape (3,)
        MAG unit base vectors resolved into the cartesian components of GEO.

    """

    mag_3 = dipole_to_vec(dipole)
    mag_2 = np.cross(np.array([0., 0., 1.]), mag_3)
    mag_2 = mag_2 / np.linalg.norm(mag_2, axis=-1, keepdims=True)

    mag_1 = np.cross(mag_2, mag_3)

    return mag_1, mag_2, mag_3


def basevectors_use(theta, phi):
    """
    Computes the unit base vectors of the local USE frame (spherical
    components).

    Parameters
    ----------
    theta : ndarray, shape (...)
        Geocentric colatitude in degrees (excluding the poles).
    phi : ndarray, shape (...)
        Longitude in degrees.

    Returns
    -------
    use_1, use_2, use_3 : ndarray, shape (..., 3)
        USE unit base vectors resolved into the cartesian components of GEO.

    """

    theta = np.array(np.radians(theta))
    phi = np.array(np.radians(phi))

    if (np.amin(theta) == 0.) or (np.amax(theta) == np.pi):
        raise ValueError("Basevectors are not defined at poles.")

    grid_shape = np.broadcast(theta, phi).shape

    # predefine output, the components of the base vectors in the last
    # dimensions: shape (..., 3, 3)
    use_1 = np.empty(grid_shape + (3,))
    use_2 = np.empty(grid_shape + (3,))
    use_3 = np.empty(grid_shape + (3,))

    # calculate and save sin/cos of angles
    sin_phi = np.sin(phi)
    sin_theta = np.sin(theta)
    cos_phi = np.cos(phi)
    cos_theta = np.cos(theta)

    # first base vector (Up)
    use_1[..., 0] = sin_theta*cos_phi
    use_1[..., 1] = sin_theta*sin_phi
    use_1[..., 2] = cos_theta

    # second base vector (South)
    use_2[..., 0] = cos_theta*cos_phi
    use_2[..., 1] = cos_theta*sin_phi
    use_2[..., 2] = -sin_theta

    # third base vector (East)
    use_3[..., 0] = -sin_phi
    use_3[..., 1] = cos_phi
    use_3[..., 2] = 0.

    return use_1, use_2, use_3


def geo_to_base(theta, phi, base_1, base_2, base_3, inverse=None):
    """
    Transform spherical geographic coordinates into rotated spherical
    coordinates as given by three cartesian unit base vectors.

    Parameters
    ----------
    theta : float or ndarray, shape (...)
        Geocentric colatitude in degrees.
    phi : float or ndarray, shape (...)
        Longitude in degrees.
    base_1, base_2, base_3 : ndarray, shape (3,) or (..., 3)
        Base vector 1 through 3 resolved into cartesian components in GEO.
    inverse : bool, optional
        Use inverse transformation instead, i.e. transform from rotated to
        spherical geographic coordinates (default is False).

    Returns
    -------
    theta : ndarray, shape (...)
        Colatitude in degrees :math:`[0^\\circ, 180^\\circ]` of the rotated
        coordinate system.
    phi : ndarray, shape (...)
        Longitude in degrees :math:`(-180^\\circ, 180^\\circ]` of the rotated
        coordinate system.

    See Also
    --------
    transform_points

    """

    inverse = False if inverse is None else inverse

    # convert spherical to cartesian (radius = 1) coordinates
    x, y, z = spherical_to_cartesian(1, theta, phi)

    if inverse:
        # components of unit base vectors are the columns of inverse matrix
        x_ref = base_1[..., 0]*x + base_2[..., 0]*y + base_3[..., 0]*z
        y_ref = base_1[..., 1]*x + base_2[..., 1]*y + base_3[..., 1]*z
        z_ref = base_1[..., 2]*x + base_2[..., 2]*y + base_3[..., 2]*z

    else:
        # components of unit base vectors are the rows of the rotation matrix
        x_ref = base_1[..., 0]*x + base_1[..., 1]*y + base_1[..., 2]*z
        y_ref = base_2[..., 0]*x + base_2[..., 1]*y + base_2[..., 2]*z
        z_ref = base_3[..., 0]*x + base_3[..., 1]*y + base_3[..., 2]*z

    # convert to spherical coordinates, discard radius as it is 1.
    _, theta_ref, phi_ref = cartesian_to_spherical(x_ref, y_ref, z_ref)

    return theta_ref, phi_ref


def transform_points(theta, phi, time=None, *, reference=None, inverse=None,
                     dipole=None):
    """
    Transform spherical geographic coordinates into rotated spherical
    coordinates.

    Parameters
    ----------
    theta : float or ndarray, shape (...)
        Geocentric colatitude in degrees.
    phi : float or ndarray, shape (...)
        Longitude in degrees.
    time : float or ndarray, shape (...)
        Time given as modified Julian date, i.e. with respect to the date 0h00
        January 1, 2000 (mjd2000). Ignored for ``reference='mag'``.
    reference : {'gsm', 'sm', 'mag'}
        Target coordinate system.
    inverse : bool
        Use inverse transformation instead, i.e. transform from rotated
        to spherical geographic coordinates (default is False).
    dipole : ndarray, shape (..., 3), or tuple of ndarrays, optional
        Dipole coefficients. Accepted input is a single array with the dipole
        coefficients :math:`g_1^0`, :math:`g_1^1` and :math:`h_1^1` in the
        trailing dimension; or a tuple of two arrays, where the first array is
        the co-latitude of the geomagentic north pole and the second is its
        longitude; or a tuple of three arrays, one array for each dipole
        coefficient in the natural order. Defaults to the SH coefficients in
        ``basicConfig['params.dipole']``.

    Returns
    -------
    theta : ndarray, shape (...)
        Geocentric colatitude in degrees :math:`[0^\\circ, 180^\\circ]` of the
        rotated coordinate system.
    phi : ndarray, shape (...)
        Longitude in degrees :math:`(-180^\\circ, 180^\\circ]` of the rotated
        geocentric coordinate system.

    See Also
    --------
    geo_to_base

    """

    reference = str(reference).lower()
    inverse = False if inverse is None else inverse

    if dipole is None:
        dipole = config_utils.basicConfig['params.dipole']

    if reference == 'gsm':
        # compute GSM base vectors
        base_1, base_2, base_3 = basevectors_gsm(time, dipole=dipole)

    elif reference == 'sm':
        # compute SM base vectors
        base_1, base_2, base_3 = basevectors_sm(time, dipole=dipole)

    elif reference == 'mag':
        # compute centered dipole base vectors
        base_1, base_2, base_3 = basevectors_mag(dipole=dipole)

    else:
        raise ValueError('Unknown target reference system. Use one of '
                         '{"gsm", "sm", "mag"}.')

    theta_base, phi_base = geo_to_base(theta, phi, base_1, base_2, base_3,
                                       inverse=inverse)

    return theta_base, phi_base


def matrix_geo_to_base(theta, phi, base_1, base_2, base_3, inverse=None):
    """
    Transform vector components in the local USE frame of GEO to components in
    the local USE frame of a rotated spherical coordinate system as given by
    three cartesian unit base vectors.

    Parameters
    ----------
    theta : float or ndarray, shape (...)
        Geocentric colatitude in degrees.
    phi : float or ndarray, shape (...)
        Longitude in degrees.
    base_1, base_2, base_3 : ndarray, shape (..., 3)
        Base vectors 1 through 3 resolved into cartesian components in GEO.
    inverse : bool
        Use inverse transformation instead, i.e. transform from rotated
        coordinates to geographic (default is False).

    Returns
    -------
    theta : ndarray, shape (...)
        Reference colatitude in degrees :math:`[0^\\circ, 180^\\circ]`.
    phi : ndarray, shape (...)
        Reference longitude in degrees :math:`(-180^\\circ, 180^\\circ]`.
    R : ndarray, shape (..., 3, 3), optional
        Stacked matrices that rotate spherical vector components from GEO to
        the rotated reference frame. The matrices (3x3) reside in the last two
        dimensions, while the leading dimensions are identical to the input
        grid.

        | B_radius_ref = B_radius
        | B_theta_ref  = R[1, 1]*B_theta + R[1, 2]*B_phi
        | B_phi_ref    = R[2, 1]*B_theta + R[2, 2]*B_phi

    See Also
    --------
    transform_vectors

    """

    inverse = False if inverse is None else inverse

    if inverse:
        theta_ref, phi_ref = theta, phi
        theta, phi = geo_to_base(theta_ref, phi_ref, base_1, base_2,
                                 base_3, inverse=True)
    else:
        theta_ref, phi_ref = geo_to_base(theta, phi, base_1, base_2, base_3)

    # matrix to rotate vector from USE at (theta, phi) to GEO
    R_use_to_geo = np.stack(basevectors_use(theta, phi), axis=-1)

    # rotate vector according to reference system defined by base vectors
    R_geo_to_ref = np.stack((base_1, base_2, base_3), axis=-2)

    # matrix to rotate vector from original USE to reference system
    R_use_to_ref = np.matmul(R_geo_to_ref, R_use_to_geo)

    # matrix to rotate reference to new USE using the transpose
    R_ref_to_use2 = np.stack(basevectors_use(theta_ref, phi_ref), axis=-2)

    # complete rotation matrix: spherical GEO to spherical reference
    R = np.matmul(R_ref_to_use2, R_use_to_ref)  # == R_use_to_use2

    if inverse:
        return theta, phi, np.swapaxes(R, -2, -1)
    else:
        return theta_ref, phi_ref, R


def transform_vectors(theta, phi, B_theta, B_phi, time=None, reference=None,
                      inverse=None, dipole=None):
    """
    Transform vector components in the local USE frame of GEO to components in
    the local USE frame of a magnetic coordinate system.

    Parameters
    ----------
    theta : float or ndarray, shape (...)
        Geocentric colatitude in degrees.
    phi : float or ndarray, shape (...)
        Longitude in degrees.
    B_theta : float or ndarray, shape (...)
        Spherical southward vector components.
    B_phi : float or ndarray, shape (...)
        Azimuthal vector components.
    time : float or ndarray, shape (...)
        Time given as modified Julian date, i.e. with respect to the date 0h00
        January 1, 2000 (mjd2000). Ignored for ``reference='mag'``.
    reference : {'gsm', 'sm', 'mag'}
        Target coordinate system.
    inverse : bool
        Use inverse transformation instead, i.e. transform coordinates and
        spherical components from the magnetic to the geographic frame (default
        is False).
    dipole : ndarray, shape (..., 3), or tuple of ndarrays, optional
        Dipole coefficients. Accepted input is a single array with the dipole
        coefficients :math:`g_1^0`, :math:`g_1^1` and :math:`h_1^1` in the
        trailing dimension; or a tuple of two arrays, where the first array is
        the co-latitude of the geomagentic north pole and the second is its
        longitude; or a tuple of three arrays, one array for each dipole
        coefficient in the natural order. Defaults to the SH coefficients in
        ``basicConfig['params.dipole']``.

    Returns
    -------
    theta : ndarray, shape (...)
        Colatitude in degrees :math:`[0^\\circ, 180^\\circ]` of the magnetic
        geocentric coordinate system.
    phi : ndarray, shape (...)
        Longitude in degrees :math:`(-180^\\circ, 180^\\circ]` of the magnetic
        coordinate system.
    B_theta : float or ndarray, shape (...)
        Spherical southward vector components in the target frame.
    B_phi : float or ndarray, shape (...)
        Azimuthal vector components in the target frame.

    See Also
    --------
    matrix_geo_to_base

    """

    inverse = False if inverse is None else inverse

    reference = str(reference).lower()

    # set the geomagnetic dipole
    if dipole is None:
        dipole = config_utils.basicConfig['params.dipole']

    if reference == 'gsm':
        # compute GSM base vectors
        base_1, base_2, base_3 = basevectors_gsm(time, dipole=dipole)

    elif reference == 'sm':
        # compute SM base vectors
        base_1, base_2, base_3 = basevectors_sm(time, dipole=dipole)

    elif reference == 'mag':
        # compute centered dipole base vectors
        base_1, base_2, base_3 = basevectors_mag(dipole=dipole)

    else:
        raise ValueError('Unknown target reference system. Use one of '
                         '{"gsm", "sm", "mag"}.')

    # combine basevectors
    theta_ref, phi_ref, R = matrix_geo_to_base(
        theta, phi, base_1, base_2, base_3, inverse=inverse)

    # transform vector components
    B_theta_ref = R[..., 1, 1]*B_theta + R[..., 1, 2]*B_phi
    B_phi_ref = R[..., 2, 1]*B_theta + R[..., 2, 2]*B_phi

    return theta_ref, phi_ref, B_theta_ref, B_phi_ref


def _qdipole_nonvectorized(year, glat, glon, height, apex):
    """Helper that calls fortranapex to compute quasi-dipole coordinates."""

    apex.set_epoch(year)
    qdlat, qdlon = apexpy.fortranapex.apxg2q(
        glat, (glon + 180) % 360 - 180, height, 0)[:2]
    f1, f2 = apexpy.fortranapex.apxg2q(
        glat, (glon + 180) % 360 - 180, height, 1)[2:4]

    return qdlat, qdlon, f1, f2


# create numpy vectorized function
_qdipole = np.vectorize(
    _qdipole_nonvectorized,
    signature='(),(),(),()->(),(),(n),(n)',
    excluded={4, 'apex'}
)


def qdipole(time, radius, theta, phi, datafile=None, fortranlib=None):
    """
    Compute quasi-dipole (QD) coordinates, magnetic local time (MLT) and
    QD basevectors for a given geographic position.

    Parameters
    ----------
    time : float or ndarray, shape (...)
        Time given as MJD2000 (modified Julian date).
    radius : float or ndarray, shape (...)
        Array containing the radius in kilometers.
    theta : float or ndarray, shape (...)
        Array containing the colatitude in degrees
        :math:`[0^\\circ,180^\\circ]`.
    phi : float or ndarray, shape (...)
        Array containing the longitude in degrees.
    datafile : str, optional
        Path to custom coefficient file (defaults to `apexsh.dat` file
        in :mod:`apexpy`).
    fortranlib : str, optional
        Path to Fortran Apex CPython library (defaults to the
        linked library file in :mod:`apexpy`.

    Returns
    -------
    qdlat : ndarray, shape (...)
        Quasi-dipole latitide in degrees.
    qdlon : ndarray, shape (...)
        Quasi-dipole longitude in degrees.
    mlt : ndarray, shape (...)
        Magnetic local time in hours.
    f1 : ndarray, shape (2, ...)
        East and north components of the first QD basevector.
    f2 : ndarray, shape (2, ...)
        East and north components of the second QD basevector.

    References
    ----------
    This function was implemented using modified code from the Apexpy package
    on `GitHub <https://github.com/aburrell/apexpy/tree/main>`_.

    """

    if not HAS_APX:
        raise ImportError('This feature requires the optional '
                          'package "apexpy".')

    # get initial epoch
    date = float(apexpy.fortranapex.igrf.datel)

    if date == 0:
        date = 2015.  # random date

    apex = apexpy.Apex(date=date, fortranlib=fortranlib, datafile=datafile)

    # coerce numpy float arrays
    time = np.asarray(time, dtype=float)
    radius = np.asarray(radius, dtype=float)
    theta = np.asarray(theta, dtype=float)
    phi = np.asarray(phi, dtype=float)

    # convert geocentric to geodetic latitude
    height, beta = geo_to_gg(radius, theta)
    glat = apexpy.helpers.checklat(90. - beta, name='glat')

    # convert time to decimal years
    year = data_utils.mjd_to_dyear(time)

    # compute apex coordinates and base vectors
    qdlat, qdlon, f1, f2 = _qdipole(year, glat, phi,
                                    height, apex=apex)

    # compute qdlon of the subsolar point
    ssgcth, ssglon = sun_position(time)
    _, ssalon, _, _ = _qdipole(year, 90. - ssgcth, ssglon,
                               height=50*6371, apex=apex)

    # compute magnetic local time
    mlt = (180. + qdlon - ssalon)/15. % 24.

    # reset epoch to initial
    apex.set_epoch(date)

    return qdlat, qdlon, mlt, f1.T, f2.T


def center_azimuth(phi):
    """
    Project azimuth angles in degrees to the semi-open interval
    :math:`(-180^\\circ, 180^\\circ]`.

    Parameters
    ----------
    phi : ndarray, float
        Azimuth in degrees.

    Returns
    -------
    phi : ndarray, float
        Azimuth in degrees on the semi-open interval
        :math:`(-180^\\circ, 180^\\circ]`.

    """

    phi = phi % 360.
    try:  # works for ndarray
        phi = np.where(phi > 180., phi - 360., phi)  # centered around prime
    except TypeError:  # catch error if float
        phi += -360. if phi > 180. else 0.

    return phi


def local_time(time, phi):
    """
    Compute local time in terms of the azimuthal distance to the prime
    meridian.

    Parameters
    ----------
    time : float, ndarray
        Time given as modified Julian date.
    phi : float, ndarray
        Azimuth in degrees.

    Returns
    -------
    local : ndarray
        Local time [0, 24).

    """

    return np.remainder(time + phi/360, 1)*24


def q_response_1D(periods, sigma, radius, n, kind=None):
    """
    Compute the response for a spherically layered conductor in an
    inducing external field of a single spherical harmonic degree.

    Parameters
    ----------
    periods : ndarray or float, shape (m,)
        Oscillation period of the inducing field in seconds.
    sigma : ndarray, shape (k,)
        Conductivity of spherical shells, starting with the outermost in (S/m).
    radius : ndarray, shape (k,)
        Radius of the interfaces in between the layers, starting with outermost
        layer in kilometers (i.e. conductor surface, see Notes).
    n : int
        Spherical degree of inducing external field.
    kind : {'quadratic', 'constant'}, optional
        Approximation for "quadratic" layers (layers of sigma with inverse
        quadratic dependence on radius) or "constant" layers (layers of
        constant sigma, last layer will be set to infinity irrespective of its
        value in ``sigma[-1]``).

    Returns
    -------
    C : ndarray, shape (m,)
        C-response in (km), complex.
    rho_a : ndarray, shape (m,)
        Electrical surface resistance in (:math:`\\Omega m`).
    phi : ndarray, shape (m,)
        Proportional to phase angle of C-response in degrees.
    Q : ndarray, shape (m,)
        Q-response, complex.

    Notes
    -----

    Option ``kind='quadratic'``:
        The following shows how the conductivity is defined in the sphercial
        shells:

        | ``radius[0]`` >= `r` > ``radius[1]``: \
            ``sigma[0]`` * ( ``radius[0]`` / `r` ) * * 2
        | ``radius[1]`` >= `r` > ``radius[2]``: \
            ``sigma[1]`` * ( ``radius[1]`` / `r` ) * * 2
        | ...
        | ``radius[k-1]`` >= `r` > 0 : \
            ``sigma[k-1]`` * ( ``radius[k-1]`` / `r` ) * * 2

        Courtesy of A. Grayver. Code based on Kuvshinov & Semenov (2012).

    Option ``kind='constant'``:
        The following shows how the conductivity is defined in the sphercial
        shells:

        | ``radius[0]`` >= `r` > ``radius[1]``: ``sigma[0]``
        | ``radius[1]`` >= `r` > ``radius[2]``: ``sigma[1]``
        | ...
        | ``radius[k-1]`` >= `r` > 0 : ``sigma[k-1]`` = ``np.inf`` \
            (:math:`\\sigma` = `\\inf`)

        There are ``k`` sphercial shells of uniform conductivity with
        radius in (km) and conductivity :math:`\\sigma` in (S/m).

        The last shell corresponds to the sphercial core whose conductivity is
        set to infinity regardless of the provided ``sigma[-1]``.

        The program should work also for very small periods, where it
        models the response of a layered plane conductor

        | Python version: August 2018, Clemens Kloss
        | Matlab version: November 2000, Nils Olsen
        | Original Fortran program: Peter Weidelt

    """

    if kind is None:
        kind = 'quadratic'

    periods = np.asarray(periods, dtype=float)  # ensure numpy array
    if periods.ndim > 1:
        raise ValueError("Input ``periods`` must be a vector.")

    sigma = np.asarray(sigma, dtype=float)  # ensure numpy array
    if sigma.ndim > 1:
        raise ValueError("Conductivity ``sigma`` must be a vector.")

    if kind == 'constant':

        nl = radius.size-2  # index of last layer, there are nl+1 layers

        eps = 1.0e-10
        zlimit = 3

        fac1 = factorial(n)
        fac2 = (-1)**n * fac1/(2*n+1)

        # initialze helpers variables and output
        C = np.empty(periods.shape, dtype=complex)
        z = np.empty((2,), dtype=complex)
        p = np.empty((2,), dtype=complex)
        q = np.empty((2,), dtype=complex)
        pd = np.empty((2,), dtype=complex)
        qd = np.empty((2,), dtype=complex)

        for counter, period in enumerate(periods):
            for il in range(nl, -1, -1):  # runs over nl...0
                k = np.sqrt(8.0e-7 * 1.0j * np.pi**2 * sigma[il] / period)
                z[0] = k*radius[il]*1000
                z[1] = k*radius[il+1]*1000

                # calculate spherical bessel functions with small argument
                # by power series (abramowitz & Stegun 10.2.5, 10.2.6
                # and 10.2.4):

                if abs(z[0]) < zlimit:
                    for m in range(2):
                        p[m] = 1+0j
                        q[m] = 1+0j
                        pd[m] = n
                        qd[m] = -(n+1)
                        zz = z[m]**2 / 2

                        j = 1
                        dp = 1+0j
                        dq = 1+0j
                        while (abs(dp) > eps or abs(dq) > eps):
                            dp = dp * zz / j / (2*j+1+2*n)
                            dq = dq * zz / j / (2*j-1-2*n)
                            p[m] = p[m] + dp
                            q[m] = q[m] + dq
                            pd[m] = pd[m] + dp*(2*j+n)
                            qd[m] = qd[m] + dq*(2*j-n-1)
                            j += 1

                        p[m] = p[m] * z[m]**n / fac1
                        q[m] = q[m] * z[m]**(-n-1) * fac2
                        q[m] = (-1)**(n+1) * np.pi/2 * (p[m]-q[m])
                        pd[m] = pd[m] * z[m]**(n-1) / fac1
                        qd[m] = qd[m] * z[m]**(-n-2) * fac2
                        qd[m] = (-1)**(n+1) * np.pi/2 * (pd[m]-qd[m])

                    v1 = p[1] / p[0]
                    v2 = pd[0] / p[0]
                    v3 = pd[1] / p[0]
                    v4 = q[0] / q[1]
                    v5 = qd[0] / q[1]
                    v6 = qd[1] / q[1]
                else:
                    # calculate spherical bessel functions with large argument
                    # the exponential behaviour is split off and treated
                    # separately (abramowitz & stegun 10.2.9 and 10.2.15)
                    for m in range(2):
                        zz = 2*z[m]
                        rm = 1+0j
                        rp = 1+0j
                        rmd = 1+0j
                        rpd = 1+0j
                        d = 1+0j
                        sg = 1+0j
                        for j in range(1, n+1):
                            d = d * (n+1-j)*(n+j) / j / zz
                            sg = -sg
                            rp = rp + d
                            rm = rm + sg*d
                            rmd = rmd + sg*d*(j+1)
                            rpd = rpd + d*(j+1)

                        e = np.exp(-2*z[m])
                        p[m] = (rm - sg*rp*e) / zz
                        q[m] = (np.pi/zz) * rp
                        pd[m] = ((rm + sg*rp*e) /
                                 zz - 2*(rmd - sg*rpd*e) / zz**2)
                        qd[m] = -q[m] - 2*np.pi*rpd / zz**2

                    e = np.exp(-(z[0] - z[1]))
                    v1 = p[1] / p[0] * e
                    v2 = pd[0] / p[0]
                    v3 = pd[1] / p[0] * e
                    v4 = q[0] / q[1] * e
                    v5 = qd[0] / q[1] * e
                    v6 = qd[1] / q[1]

                if (il == nl):
                    b = k*(v2 - v5*v1) / (1 - v4*v1)
                else:
                    b = (k*((v2 - v5*v1)*b + k*(v5*v3-v2*v6)) /
                         ((1 - v4*v1)*b + k*(v4*v3 - v6)))

            C[counter] = radius[0] / (1+1000*radius[0]*b)  # C in km
            print("Finished {:.1f}%".format(
                (counter+1)/periods.size*100), end='\r')

        print('')

        # if nargout > 1
        rho_a = 1e-7*8*np.pi**2 / periods * np.abs(C*1000)**2
        phi = 90 + 57.3*np.angle(C)
        Q = n/(n+1) * (1 - (n+1)*C/radius[0]) / (1 + n*C/radius[0])

    elif kind == 'quadratic':

        radius = 1e3*np.asarray(radius, dtype=float)

        # constants
        mu = 4*np.pi*1e-7

        omega = 2*np.pi*1.0j/periods

        # Number of layers
        N = sigma.size
        M = omega.size

        # Preallocate
        Y = np.zeros((M, N), dtype=complex)

        # values for inner sphere, r = N (core)
        qk = -omega*mu*radius[-1]
        bk = np.sqrt((n+0.5)**2 - qk*sigma[-1]*radius[-1])
        bkp = bk + 0.5
        Y[:, -1] = -bkp/qk

        # Loop over all layers above core (from core to surface)
        # from before last (N-2) to first (0)
        for k in range(N-2, -1, -1):
            # Compute temporary scalars
            qk = -omega*mu*radius[k]
            bk = np.sqrt((n+0.5)**2 - qk*sigma[k]*radius[k])
            bkp = bk + 0.5
            bkm = bk - 0.5

            etak = radius[k]/radius[k+1]
            zetak = etak**(2*bk)

            tauk = (1. - zetak) / (1. + zetak)
            # handling of precision overflow due to high frequencies
            tauk[np.isnan(tauk)] = -1.

            qk = -omega*mu*radius[k]
            qk1 = -omega*mu*radius[k+1]
            qY = qk1*Y[:, k+1]

            # Admittance for this layer
            Y[:, k] = 1/qk*(qY*(bk-0.5*tauk)+bkp*bkm*tauk)/(bk+tauk*(0.5+qY))

        # Compute the C-response (in km)
        C = 1/(omega*mu*Y[:, 0])/1e3

        rho_a = mu*omega*np.abs(C*1000)**2  # rho_a in (Ohm*m)
        phi = 90 + 57.3*np.angle(C)  # phase phi in degrees

        # Q-response
        Q = n/(n+1)*(1-(n+1)*C/(radius[0]/1e3))/(1+n*C/(radius[0]/1e3))

    else:
        raise ValueError(f'Unknown option "kind={kind}".')

    return C, rho_a, phi, Q


def q_response(frequency, nmax):
    """
    Compute the Q-response for a given conductivity model of Earth.

    The conductivity model is loaded during the computation from
    ``basicConfig['file.Earth_conductivity']``.

    Parameters
    ----------
    frequency : ndarray, shape (N,)
        Vector of `N` frequencies (1/sec) for which to compute the Q-response.
    nmax : int
        Maximum spherical harmonic degree of inducing field.

    Returns
    -------
    q_response : ndarray, shape (nmax, N)
        Q-response for every frequency and harmonic degree of inducing
        field. Index 0 corresponds to degree 1, index 1 corresponds to degree
        2, and so on.

    """

    # load conductivity model
    filepath = config_utils.basicConfig['file.Earth_conductivity']
    sigma_model = np.loadtxt(filepath)

    radius_ref = 6371.2  # reference radius in km

    # unpack file: depth and layer conductivity
    # convert depth to radius
    sigma_radius = radius_ref - sigma_model[:, 0]

    # conductivity profile
    sigma = sigma_model[:, 1]

    # find all harmonic terms
    index = frequency > 0.0

    periods = 1 / frequency[index]

    q_response = np.zeros((nmax, frequency.size), dtype=complex)
    for n in range(nmax):
        print('Calculating Q-response for degree {:}'.format(n+1))
        # compute Q-response for conductivity model and given degree n
        C_n, rho_n, phi_n, Q_n = q_response_1D(
            periods, sigma, sigma_radius, n+1, kind='quadratic')
        q_response[n, index] = Q_n  # index 0: degree 1, index 1: degree 2, ...

    return q_response
