# Copyright (C) 2025 Clemens Kloss
#
# This file is part of ChaosMagPy.
#
# ChaosMagPy is released under the MIT license. See LICENSE in the root of the
# repository for full licensing details.

"""
`chaosmagpy.data_utils` provides functions for loading and writing data and
geomagnetic field models. It also offers functions to do common time
conversions.

.. autosummary::
    :toctree: functions

    load_matfile
    load_RC_datfile
    save_RC_h5file
    load_shcfile
    save_shcfile
    mjd2000
    timestamp
    is_leap_year
    dyear_to_mjd
    mjd_to_dyear
    memory_usage
    gauss_units

"""


import pandas as pd
import numpy as np
import hdf5storage as hdf
import warnings
import h5py
import os
import datetime as dt
import textwrap


def load_matfile(filepath, variable_names=None, **kwargs):
    """
    Load MAT-file and return dictionary.

    Function loads MAT-file by traversing the structure converting data into
    low-level numpy arrays of different types. There is no guarantee that any
    kind of data is read in correctly. The data dtype can also vary depending
    on the MAT-file (v7.3 returns floats instead of integers). But it should
    work identically for v7.3 and prior MAT-files. Arrays are squeezed if
    possible. Relies on the :mod:`hdf5storage` package.

    Parameters
    ----------
    filepath : str
        Filepath and name of MAT-file.
    variable_names : list of strings
        Top-level variables to be loaded.
    **kwargs : keywords
        Additional keyword arguments are passed to :func:`hdf5storage.loadmat`.

    Returns
    -------
    data : dict
        Dictionary containing the data as dictionaries or numpy arrays.

    """

    # define a recursively called function to traverse structure
    def traverse_struct(struct):

        # for dictionaries, iterate through keys
        if isinstance(struct, dict):
            out = dict()
            for key, value in struct.items():
                out[key] = traverse_struct(value)
            return out

        # for ndarray, iterate through dtype names
        elif isinstance(struct, np.ndarray):

            # collect dtype names if available
            names = struct.dtype.names

            # if no fields in array
            if names is None:
                if struct.dtype == np.dtype('O') and struct.shape == (1, 1):
                    return traverse_struct(struct[0, 0])
                else:
                    return struct.squeeze()

            else:  # if there are fields, iterate through fields
                out = dict()
                for name in names:
                    out[name] = traverse_struct(struct[name])
                return out

        else:
            return struct

    output = hdf.loadmat(filepath, variable_names=variable_names, **kwargs)

    # loadmat returns dictionary, go through keys and call traverse_struct
    for key, value in output.items():
        if key.startswith('__') and key.endswith('__'):
            pass
        else:
            output[key] = traverse_struct(value)

    return output


def load_RC_datfile(filepath=None, parse_dates=None):
    """
    Load RC-index data file into pandas data frame.

    Parameters
    ----------
    filepath : str, optional
        Filepath to RC index ``*.dat``. If ``None``, the RC
        index will be fetched from :rc_url:`spacecenter.dk <>`.
    parse_dates : bool, optional
        Replace index with datetime object for time-series manipulations.
        Default is ``False``.

    Returns
    -------
    df : dataframe
        Pandas dataframe with names {'time', 'RC', 'RC_e', 'RC_i', 'flag'},
        where ``'time'`` is given in modified Julian dates.

    """

    if filepath is None:
        from lxml import html
        import requests
        import urllib

        link = "http://www.spacecenter.dk/files/magnetic-models/RC/"

        page = requests.get(link)
        print(f'Accessing {page.url}.')

        tree = html.fromstring(page.content)
        hrefs = tree.xpath('//a/@href')  # find all links

        for href in hrefs:
            if 'RC/current' in href:
                filepath = href
                break

        resp = urllib.request.urlopen(filepath, timeout=30)

        print(f'Downloading RC-index file "{os.path.basename(filepath)}" '
              f'(last modified on {resp.headers["last-modified"]}).')

    column_names = ['time', 'RC', 'RC_e', 'RC_i', 'flag']
    column_types = {'time': 'float64', 'RC': 'float64', 'RC_e': 'float64',
                    'RC_i': 'float64', 'flag': 'category'}

    df = pd.read_csv(filepath, sep=r'\s+', comment='#',
                     dtype=column_types, names=column_names)

    parse_dates = False if parse_dates is None else parse_dates

    # set datetime as index
    if parse_dates:
        df.index = pd.to_datetime(
            df['time'].values, unit='D', origin=pd.Timestamp('2000-1-1'))
        df.drop(['time'], axis=1, inplace=True)  # delete redundant time column

    return df


def save_RC_h5file(filepath, read_from=None):
    """
    Return HDF5-file of the RC index.

    Parameters
    ----------
    filepath : str
        Filepath and name of ``*.h5`` output file.
    read_from : str, optional
        Filepath of RC index ``*.dat``. If ``None``, the RC
        index will be fetched from :rc_url:`spacecenter.dk <>`.

    Notes
    -----
    Saves an HDF5-file of the RC index with keywords
    ['time', 'RC', 'RC_e', 'RC_i', 'flag']. Time is given in modified Julian
    dates 2000.

    Examples
    --------
    Save RC-index TXT-file (``RC_1997-2020_Aug_v4.dat``) as file in HDF5 format
    (``RC_index.h5``).

    >>> save_RC_h5file('RC_index.h5', read_from='RC_1997-2020_Aug_v4.dat')
    Successfully saved to RC_index.h5.

    """

    try:
        df_rc = load_RC_datfile(read_from, parse_dates=False)

        with h5py.File(filepath, 'w') as f:

            for column in df_rc.columns:
                variable = df_rc[column].values
                if column == 'flag':
                    dset = f.create_dataset(column, variable.shape, dtype="S1")
                    dset[:] = variable.astype('bytes')

                else:
                    f.create_dataset(column, data=variable)  # just save floats

            print(f'Successfully saved to {f.filename}.')

    except Exception as err:
        warnings.warn(f"Can't save new RC index. Raised exception: '{err}'.")


def load_shcfile(filepath, leap_year=None, comment=None):
    """
    Load SHC-file and return coefficient arrays.

    Parameters
    ----------
    filepath : str
        File path to spherical harmonic coefficient SHC-file.
    leap_year : {True, False}, optional
        Take leap year in time conversion into account (default). Otherwise,
        use conversion factor of 365.25 days per year.
    comment : str, optional
        Character at the start of a line to indicate a comment
        (defaults to ``#``). This can also be a tuple of characters.

    Returns
    -------
    time : ndarray, shape (N,)
        Array containing `N` times for each model snapshot in modified
        Julian dates with origin January 1, 2000 0:00 UTC.
    coeffs : ndarray, shape (nmax(nmax+2), N)
        Coefficients of model snapshots. Each column is a snapshot up to
        spherical degree and order `nmax`.
    parameters : dict, {'SHC', 'nmin', 'nmax', 'N', 'order', 'step'}
        Dictionary containing parameters of the model snapshots and the
        following keys: ``'SHC'`` SHC-file name, ``'nmin'`` minimum degree,
        ``'nmax'`` maximum degree, ``'N'`` number of snapshot models,
        ``'order'`` piecewise polynomial order and ``'step'`` number of
        snapshots until next break point. Extract break points of the
        piecewise polynomial with ``breaks = time[::step]``.

    """

    leap_year = True if leap_year is None else leap_year
    comment = '#' if comment is None else comment

    first_line = True

    with open(filepath, 'r') as f:

        data = np.array([])
        for line in f.readlines():

            if line.strip().startswith(comment):
                continue

            newline = np.fromstring(line, sep=' ')

            if first_line:  # first non-comment line contains shc params
                name = os.path.split(filepath)[1]  # file name string
                values = [name] + newline.astype(int).tolist()

                first_line = False

            else:
                data = np.append(data, newline)

        # unpack parameter line
        keys = ['SHC', 'nmin', 'nmax', 'N', 'order', 'step']
        parameters = dict(zip(keys, values))

        time = data[:parameters['N']]
        coeffs = data[parameters['N']:].reshape((-1, parameters['N']+2))
        coeffs = coeffs[:, 2:].copy()  # discard columns with n and m

        mjd = dyear_to_mjd(time, leap_year=leap_year)

    return mjd, coeffs, parameters


def save_shcfile(time, coeffs, order=None, filepath=None, nmin=None, nmax=None,
                 leap_year=None, header=None):
    """
    Save Gauss coefficients as SHC-file.

    Parameters
    ----------
    time : float, list, ndarray, shape (n,)
        Time of model coeffcients in modified Julian date.
    coeffs : ndarray, shape (N,) or (n, N)
        Gauss coefficients as vector or array. The first dimension of the array
        must be equal to the length `n` of the given ``time``.
    order : int, optional (defaults to 1)
        Order of the piecewise polynomial with which the coefficients are
        parameterized in time (breaks are given by ``time[::order]``).
    filepath : str, optional
        Filepath and name of the output file. Defaults to the current working
        directory and filename `model.shc`.
    nmin : int, optional
        Minimum spherical harmonic degree (defaults to 1). This will remove
        first values from coeffs if greater than 1.
    nmax : int, optional
        Maximum spherical harmonic degree (defaults to degree compatible with
        number of coeffcients, otherwise coeffcients are truncated).
    leap_year : {True, False}, optional
        Take leap years for decimal year conversion into account
        (defaults to ``True``).
    header : str, optional
        Optional header at beginning of file. Defaults to writing out a header
        indicating the timestamp and the leap year setting (``header=None``).
        Use ``header=False`` if no header should be included.
    """

    time = np.asarray(time, dtype=float)

    order = 1 if order is None else int(order)

    nmin = 1 if nmin is None else int(nmin)

    if nmax is None:
        nmax = int(np.sqrt(coeffs.shape[-1] + 1) - 1)
    else:
        nmax = int(nmax)

    if nmin > nmax:
        raise ValueError('``nmin`` must be smaller than or equal to ``nmax``.')

    filepath = 'model.shc' if filepath is None else filepath

    leap_year = True if leap_year is None else bool(leap_year)

    if coeffs.ndim == 1:
        coeffs = coeffs.reshape((1, -1))

    coeffs = coeffs[:, (nmin**2-1):((nmax+1)**2-1)]

    # compute all possible degree and orders
    deg = np.array([], dtype=int)
    ord = np.array([], dtype=int)
    for n in range(nmin, nmax+1):
        deg = np.append(deg, np.repeat(n, 2*n+1))
        ord = np.append(ord, [0])
        for m in range(1, n+1):
            ord = np.append(ord, [m, -m])

    if (header is None) or (header is True):
        header = textwrap.dedent(f"""\
        # Created on {dt.datetime.now(dt.timezone.utc)} UTC.
        # Leap years are accounted for in decimal years format ({leap_year}).
        """)
    elif header is False:
        header = ''
    else:
        header = str(header).rstrip() + '\n'

    parameter_line = f'{nmin} {nmax} {time.size} {order} {order-1}\n'

    with open(filepath, 'w') as f:
        # write header and parameter line
        f.write(header)
        f.write(parameter_line)

        f.write(f'{"":4s} {"":4s}')  # to represent the two columns for n and m
        for t in time:
            f.write(' {:16.8f}'.format(mjd_to_dyear(t, leap_year=leap_year)))
        f.write('\n')

        # write coefficient table to 8 significants
        for row, (n, m) in enumerate(zip(deg, ord)):

            f.write('{:4d} {:4d}'.format(n, m))

            for value in coeffs[:, row]:
                f.write(' {:16.8f}'.format(value))

            f.write('\n')

    print('Created SHC-file {}.'.format(
        os.path.join(os.getcwd(), filepath)))


def mjd2000(year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0,
            nanosecond=0):
    """
    Computes the modified Julian date as floating point number (epoch 2000).

    It assigns 0 to 0h00 January 1, 2000. Leap seconds are not accounted for.

    Parameters
    ----------
    time : :class:`datetime.datetime`, ndarray, shape (...)
        Datetime class instance, `OR ...`
    year : int, ndarray, shape (...)
    month : int, ndarray, shape (...), optional
        Month of the year `[1, 12]` (defaults to 1).
    day : int, ndarray, shape (...), optional
        Day of the corresponding month (defaults to 1).
    hour : int , ndarray, shape (...), optional
        Hour of the day (default is 0).
    minute : int, ndarray, shape (...), optional
        Minutes (default is 0).
    second : int, ndarray, shape (...), optional
        Seconds (default is 0).
    microsecond : int, ndarray, shape (...), optional
        Microseconds (default is 0).
    nanosecond : int, ndarray, shape (...), optional
        Nanoseconds (default is 0).

    Returns
    -------
    time : ndarray, shape (...)
        Modified Julian date (units of days).

    Examples
    --------
    >>> a = np.array([datetime.datetime(2000, 1, 1), \
datetime.datetime(2002, 3, 4)])
    >>> mjd2000(a)
        array([  0., 793.])

    >>> mjd2000(2003, 5, 3, 13, 52, 15)  # May 3, 2003, 13:52:15 (hh:mm:ss)
        1218.5779513888888

    >>> mjd2000(np.arange(2000, 2005))  # January 1 in each year
        array([   0.,  366.,  731., 1096., 1461.])

    >>> mjd2000(np.arange(2000, 2005), 2, 1)  # February 1 in each year
        array([  31.,  397.,  762., 1127., 1492.])

    >>> mjd2000(np.arange(2000, 2005), 2, np.arange(1, 6))
        array([  31.,  398.,  764., 1130., 1496.])

    """

    year = np.asarray(year)

    if (np.issubdtype(year.dtype, np.dtype(dt.datetime).type) or
            np.issubdtype(year.dtype, np.datetime64)):
        datetime = year.astype('datetime64[ns]')

    else:
        # build iso datetime string with str_ (supported in NumPy >= 2.0)
        year = np.asarray(year, dtype=np.str_)
        month = np.char.zfill(np.asarray(month, dtype=np.str_), 2)
        day = np.char.zfill(np.asarray(day, dtype=np.str_), 2)

        year_month = np.char.add(np.char.add(year, '-'), month)
        datetime = np.char.add(np.char.add(year_month, '-'), day)

        datetime = datetime.astype('datetime64[ns]')

        # not use iadd here because it doesn't broadcast arrays
        datetime = (datetime + np.asarray(hour, dtype='timedelta64[h]')
                    + np.asarray(minute, dtype='timedelta64[m]')
                    + np.asarray(second, dtype='timedelta64[s]')
                    + np.asarray(microsecond, dtype='timedelta64[us]')
                    + np.asarray(nanosecond, dtype='timedelta64[ns]'))

    nanoseconds = datetime - np.datetime64('2000-01-01', 'ns')

    return nanoseconds / np.timedelta64(1, 'D')  # fraction of days


def timestamp(time):
    """
    Convert modified Julian date to NumPy's datetime format.

    Parameters
    ----------
    time : ndarray, shape (...)
        Modified Julian date (units of days).

    Returns
    -------
    time : ndarray, shape (...)
        Array of ``numpy.datetime64[ns]``.

    Examples
    --------
    >>> timestamp(0.53245)
        numpy.datetime64('2000-01-01T12:46:43.680000000')

    >>> timestamp(np.linspace(0., 1.5, 2))
        array(['2000-01-01T00:00:00.000000000', \
'2000-01-02T12:00:00.000000000'], dtype='datetime64[ns]')

    """

    # convert mjd2000 to timedelta64[ns]
    ns = np.asarray(time) * 86400e9 * np.timedelta64(1, 'ns')

    # add datetime offset with ns precision
    return ns + np.datetime64('2000-01-01', 'ns')


def is_leap_year(year):
    """
    Determine if input year is a leap year.

    Parameters
    ----------
    year : int, ndarray, shape (...)
        Years to test for leap year.

    Returns
    -------
    leap_year : ndarray of bools, shape (...)
        ``True`` for leap year in array.

    Examples
    --------
    >>> is_leap_year([2000, 2001, 2004])
        array([ True, False,  True])

    Raises
    ------
    TypeError if ``year`` is not of type integer.

    """

    year = np.asarray(year)

    if not np.issubdtype(year.dtype, int):
        raise TypeError('Expected integer values as the input year. Use '
                        'numpy.floor to extract the integer year '
                        'from decimal years.')

    return np.logical_and(np.remainder(year, 4) == 0,
                          np.logical_or(np.remainder(year, 100) != 0,
                                        np.remainder(year, 400) == 0))


def dyear_to_mjd(time, leap_year=None):
    """
    Convert time from decimal years to modified Julian date 2000.

    Leap years are accounted for by default.

    Parameters
    ----------
    time : float, ndarray, shape (...)
        Time in decimal years.
    leap_year : {True, False}, optional
        Take leap years into account by using a conversion factor of 365 or 366
        days in a year (leap year, used by default). If ``False`` a conversion
        factor of 365.25 days in a year is used.

    Returns
    -------
    time : ndarray, shape (...)
        Time in modified Julian date 2000.

    Examples
    --------
    >>> dyear_to_mjd([2000.5, 2001.5])  # account for leap years
        array([183. , 548.5])

    >>> dyear_to_mjd([2000.5, 2001.5], leap_year=False)
        array([182.625, 547.875])

    """

    leap_year = True if leap_year is None else leap_year

    if leap_year:
        year = np.asarray(np.floor(time), dtype=int)  # note: -0.1 is year -1
        frac_of_year = np.remainder(time, 1.)

        isleap = is_leap_year(year)  # do provide integer years
        days_per_year = np.where(isleap, 366., 365.)

        days = frac_of_year * days_per_year

        mjd = mjd2000(year, 1, 1) + days

    elif not leap_year:
        days_per_year = 365.25

        mjd = (np.asarray(time) - 2000.0) * days_per_year

    else:
        raise ValueError('Unknown leap year option: use either True or False')

    return mjd


def mjd_to_dyear(time, leap_year=None):
    """
    Convert time from modified Julian date 2000 to decimal years.

    Leap years are accounted for by default.

    Parameters
    ----------
    time : float, ndarray, shape (...)
        Time in modified Julian date 2000.
    leap_year : {True, False}, optional
        Take leap years into account by using a conversion factor of 365 or 366
        days in a year (leap year, used by default). If ``False`` a conversion
        factor of 365.25 days in a year is used.

    Returns
    -------
    time : ndarray, shape (...)
        Time in decimal years.

    Examples
    --------
    >>> mjd_to_dyear([183. , 548.5])  # account for leap years
        array([2000.5, 2001.5])

    >>> mjd_to_dyear([0. , -1., 365.])
        array([2000., 1999.99726027, 2000.99726776])

    >>> mjd_to_dyear([182.625, 547.875], leap_year=False)
        array([2000.5, 2001.5])

    """

    leap_year = True if leap_year is None else leap_year

    if leap_year:
        date = (np.asarray(np.floor(time), dtype=int)*np.timedelta64(1, 'D')
                + np.datetime64('2000-01-01'))  # only precise to date

        year = date.astype('datetime64[Y]').astype(int) + 1970
        days = np.asarray(time) - mjd2000(year, 1, 1)  # days of that year

        isleap = is_leap_year(year)
        days_per_year = np.where(isleap, 366., 365.)

        dyear = year + days / days_per_year

    elif not leap_year:
        dyear = np.asarray(time) / 365.25 + 2000.

    else:
        raise ValueError('Unknown leap year option: use either True or False')

    return dyear


def memory_usage(pandas_obj):
    """
    Compute memory usage of pandas object.

    For full report, use: ``df.info(memory_usage='deep')``.

    """

    if isinstance(pandas_obj, pd.DataFrame):
        usage_b = pandas_obj.memory_usage(deep=True).sum()
    else:  # we assume if not a df it's a series
        usage_b = pandas_obj.memory_usage(deep=True)
    usage_mb = usage_b / 1024 ** 2  # convert bytes to megabytes
    return "{:03.2f} MB".format(usage_mb)


def gauss_units(deriv=None):
    """
    Return string of the magnetic field units given the derivative with time.

    String is meant to be used in plot labels.

    Parameters
    ----------
    deriv : int, optional
        Derivative (defaults to 0).

    Returns
    -------
    units : str
        Tex-style unit string.

    Examples
    --------
    >>> gauss_units()
        'nT'

    >>> gauss_units(1)
        '$\\\\mathrm{nT}/\\\\mathrm{yr}$'

    >>> gauss_units(2)
        '$\\\\mathrm{nT}/\\\\mathrm{yr}^{2}$'

    """

    deriv = 0 if deriv is None else deriv

    if deriv == 0:
        units = 'nT'
    elif deriv == 1:
        units = '$\\mathrm{{nT}}/\\mathrm{{yr}}$'
    else:
        units = '$\\mathrm{{nT}}/\\mathrm{{yr}}^{{{:}}}$'.format(deriv)

    return units
