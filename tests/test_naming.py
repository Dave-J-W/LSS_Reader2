"""File names proposed for exports (F105, Q-REF-6), lss_core.naming."""
from lss_core import naming


def test_scans_tags():
    assert naming.scans_tag([9, 6, 7, 8]) == 'S6-9'
    assert naming.scans_tag([6, 8, 11]) == 'S6_8_11'
    assert naming.scans_tag([12]) == 'S12'
    assert naming.scans_tag([]) == ''


def test_the_sample_from_the_series_macro():
    assert naming.sample_from_macro('dppc_xr.do') == 'dppc'
    assert naming.sample_from_macro('do do_files/lipid_A_gid.do') == 'lipid_A'
    assert naming.sample_from_macro('water.mac') == 'water'
    assert naming.sample_from_macro('_xr.do') == 'xr'            # nothing but the measurement word: kept
    assert naming.sample_from_macro('') == '' and naming.sample_from_macro(None) == ''


def test_the_proposed_base_name():
    assert naming.export_base('/data/2026sep/20260923', [6, 7, 8, 9]) == '20260923_S6-9'
    assert naming.export_base('/data/run 3/sample', [1, 2], 'dppc') == 'sample_dppc_S1-2'
    assert naming.export_base('a b/c?d', [3], 'x/y z') == 'c_d_x_y_z_S3'      # only safe characters
    assert naming.export_base('', []) == 'export'
