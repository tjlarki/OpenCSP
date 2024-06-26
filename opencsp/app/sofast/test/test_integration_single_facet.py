"""Integration test. Testing processing of a 'single_facet' type optic.
"""

import glob
import os
import unittest

import numpy as np

from opencsp.app.sofast.lib.DisplayShape import DisplayShape
from opencsp.app.sofast.lib.DefinitionFacet import DefinitionFacet
from opencsp.app.sofast.lib.ImageCalibrationScaling import ImageCalibrationScaling
from opencsp.app.sofast.lib.MeasurementSofastFringe import MeasurementSofastFringe
from opencsp.app.sofast.lib.ProcessSofastFringe import ProcessSofastFringe
from opencsp.app.sofast.lib.SpatialOrientation import SpatialOrientation
from opencsp.common.lib.camera.Camera import Camera
from opencsp.common.lib.deflectometry.Surface2DPlano import Surface2DPlano
from opencsp.common.lib.deflectometry.Surface2DParabolic import Surface2DParabolic
from opencsp.common.lib.geometry.Vxyz import Vxyz
from opencsp.common.lib.opencsp_path.opencsp_root_path import opencsp_code_dir
from opencsp.common.lib.tool.hdf5_tools import load_hdf5_datasets


class TestSingle(unittest.TestCase):
    @classmethod
    def setUpClass(cls, base_dir: str | None = None):
        """Sets up class

        Parameters
        ----------
        base_dir : str | None, optional
            Sets base directory. If None, uses 'data' directory in directory
            contianing file, by default None
        """
        # Get test data location
        if base_dir is None:
            base_dir = os.path.join(opencsp_code_dir(), 'test/data/sofast_fringe')

        # Find all test files
        cls.files_dataset = glob.glob(os.path.join(base_dir, 'data_expected_facet/data*.h5'))
        cls.files_dataset.sort()
        if len(cls.files_dataset) == 0:
            raise ValueError('No single-facet datsets found.')

        # Define component files
        file_measurement = os.path.join(base_dir, 'data_measurement/measurement_facet.h5')

        # Load components
        measurement = MeasurementSofastFringe.load_from_hdf(file_measurement)

        # Initialize data containers
        cls.slopes = []
        cls.surf_coefs = []
        cls.v_surf_points_facet = []

        # Load data from all datasets
        for file_dataset in cls.files_dataset:
            # Load display
            camera = Camera.load_from_hdf(file_dataset)
            orientation = SpatialOrientation.load_from_hdf(file_dataset)
            calibration = ImageCalibrationScaling.load_from_hdf(file_dataset)
            display = DisplayShape.load_from_hdf(file_dataset)

            # Calibrate measurement
            measurement.calibrate_fringe_images(calibration)

            # Load surface definition
            surface_data = load_hdf5_datasets(
                [
                    'DataSofastInput/surface_params/facet_000/surface_type',
                    'DataSofastInput/surface_params/facet_000/robust_least_squares',
                    'DataSofastInput/surface_params/facet_000/downsample',
                ],
                file_dataset,
            )
            surface_data['robust_least_squares'] = bool(surface_data['robust_least_squares'])
            if surface_data['surface_type'] == 'parabolic':
                surface_data.update(
                    load_hdf5_datasets(
                        ['DataSofastInput/surface_params/facet_000/initial_focal_lengths_xy'], file_dataset
                    )
                )
                surface = Surface2DParabolic(
                    surface_data['initial_focal_lengths_xy'],
                    surface_data['robust_least_squares'],
                    surface_data['downsample'],
                )
            else:
                surface = Surface2DPlano(surface_data['robust_least_squares'], surface_data['downsample'])

            # Load optic data
            facet_data = load_hdf5_datasets(
                [
                    'DataSofastInput/optic_definition/facet_000/v_centroid_facet',
                    'DataSofastInput/optic_definition/facet_000/v_facet_corners',
                ],
                file_dataset,
            )
            facet_data = DefinitionFacet(Vxyz(facet_data['v_facet_corners']), Vxyz(facet_data['v_centroid_facet']))

            # Load sofast params
            datasets = [
                'DataSofastInput/sofast_params/mask_hist_thresh',
                'DataSofastInput/sofast_params/mask_filt_width',
                'DataSofastInput/sofast_params/mask_filt_thresh',
                'DataSofastInput/sofast_params/mask_thresh_active_pixels',
                'DataSofastInput/sofast_params/mask_keep_largest_area',
                'DataSofastInput/sofast_params/perimeter_refine_axial_search_dist',
                'DataSofastInput/sofast_params/perimeter_refine_perpendicular_search_dist',
                'DataSofastInput/sofast_params/facet_corns_refine_step_length',
                'DataSofastInput/sofast_params/facet_corns_refine_perpendicular_search_dist',
                'DataSofastInput/sofast_params/facet_corns_refine_frac_keep',
            ]
            params = load_hdf5_datasets(datasets, file_dataset)

            # Instantiate sofast object
            sofast = ProcessSofastFringe(measurement, orientation, camera, display)

            # Update parameters
            sofast.params.mask_hist_thresh = params['mask_hist_thresh']
            sofast.params.mask_filt_width = params['mask_filt_width']
            sofast.params.mask_filt_thresh = params['mask_filt_thresh']
            sofast.params.mask_thresh_active_pixels = params['mask_thresh_active_pixels']
            sofast.params.mask_keep_largest_area = params['mask_keep_largest_area']

            sofast.params.geometry_params.perimeter_refine_axial_search_dist = params[
                'perimeter_refine_axial_search_dist'
            ]
            sofast.params.geometry_params.perimeter_refine_perpendicular_search_dist = params[
                'perimeter_refine_perpendicular_search_dist'
            ]
            sofast.params.geometry_params.facet_corns_refine_step_length = params['facet_corns_refine_step_length']
            sofast.params.geometry_params.facet_corns_refine_perpendicular_search_dist = params[
                'facet_corns_refine_perpendicular_search_dist'
            ]
            sofast.params.geometry_params.facet_corns_refine_frac_keep = params['facet_corns_refine_frac_keep']

            # Run SOFAST
            sofast.process_optic_singlefacet(facet_data, surface)

            # Store test data
            cls.slopes.append(sofast.data_characterization_facet[0].slopes_facet_xy)
            cls.surf_coefs.append(sofast.data_characterization_facet[0].surf_coefs_facet)
            cls.v_surf_points_facet.append(sofast.data_characterization_facet[0].v_surf_points_facet.data)

    def test_slopes(self):
        datasets = ['DataSofastCalculation/facet/facet_000/slopes_facet_xy']
        for idx, file in enumerate(self.files_dataset):
            with self.subTest(i=idx):
                data = load_hdf5_datasets(datasets, file)
                np.testing.assert_allclose(data['slopes_facet_xy'], self.slopes[idx], atol=1e-7, rtol=0)

    def test_surf_coefs(self):
        datasets = ['DataSofastCalculation/facet/facet_000/surf_coefs_facet']
        for idx, file in enumerate(self.files_dataset):
            with self.subTest(i=idx):
                data = load_hdf5_datasets(datasets, file)
                np.testing.assert_allclose(data['surf_coefs_facet'], self.surf_coefs[idx], atol=1e-8, rtol=0)

    def test_int_points(self):
        datasets = ['DataSofastCalculation/facet/facet_000/v_surf_points_facet']
        for idx, file in enumerate(self.files_dataset):
            with self.subTest(i=idx):
                data = load_hdf5_datasets(datasets, file)
                np.testing.assert_allclose(
                    data['v_surf_points_facet'], self.v_surf_points_facet[idx], atol=1e-8, rtol=0
                )


if __name__ == '__main__':
    unittest.main()
