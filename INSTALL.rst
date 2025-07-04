Installation
============

ChaosMagPy relies on the following (some are optional):

* python>=3.6
* numpy<=1.26 (loading MAT-files fails in v2.0, waiting for fix in hdf5storage)
* scipy
* pandas
* cython
* h5py
* hdf5storage>0.1.17
* pyshp>=2.3.1
* apexpy (optional, used for evaluating the ionospheric E-layer field)
* matplotlib>=3.6 (optional, used for plotting)
* lxml (optional, used for downloading latest RC-index file)

Specific installation steps using the conda/pip package managers are as follows:

1. Install packages with conda:

   >>> conda install python "numpy<2" scipy pandas cython pyshp h5py matplotlib lxml

2. Install remaining packages with pip:

   >>> pip install hdf5storage apexpy

3. Finally install ChaosMagPy with pip:

   >>> pip install chaosmagpy

   or, if all optional packages are desired,

   >>> pip install 'chaosmagpy[full]'

   Alternatively, if you have downloaded the distribution archives from the
   Python Package Index (PyPI) at https://pypi.org/project/chaosmagpy/#files,
   install ChaosMagPy using the built or source distributions:

   >>> pip install chaosmagpy-x.x-py3-none-any.whl

   or

   >>> pip install chaosmagpy-x.x.tar.gz

   replacing  ``x.x`` with the relevant version.
