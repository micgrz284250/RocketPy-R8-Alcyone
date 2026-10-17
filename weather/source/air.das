Attributes {
    lat {
        String units "degrees_north";
        Float32 actual_range 90.0, -90.0;
        String long_name "Latitude";
        String standard_name "latitude";
        String axis "Y";
    }
    lon {
        String units "degrees_east";
        String long_name "Longitude";
        Float32 actual_range 0.0, 357.5;
        String standard_name "longitude";
        String axis "X";
    }
    level {
        String units "millibar";
        Float32 actual_range 1000.0, 10.0;
        String long_name "Level";
        String positive "down";
        Int16 GRIB_id 100;
        String GRIB_name "hPa";
        String axis "Z";
    }
    time {
        String long_name "Time";
        String delta_t "0000-00-00 06:00:00";
        String standard_name "time";
        String axis "T";
        String units "hours since 1800-01-01 00:00:0.0";
        String avg_period "0030-00-00 00:00:00";
        String climatology "climatology_bounds";
        String climo_period "1991/01/01 00Z - 2020/12/31 18Z";
        Float64 actual_range -1.5769752E7, -1.5760998E7;
        Float64 ltm_range 1674264.0, 1937250.0;
    }
    climatology_bounds {
        String long_name "Climate Time Boundaries";
        String units "hours since 1800-01-01 00:00:0.0";
    }
    air {
        String long_name "Long Term Mean 4xDaily Air temperature";
        String units "degK";
        Int16 precision 2;
        Int16 least_significant_digit 1;
        Int16 GRIB_id 11;
        String GRIB_name "TMP";
        String var_desc "Air temperature";
        String level_desc "Pressure Levels";
        String statistic "Long Term Mean";
        String parent_stat "Individual Obs";
        Float32 missing_value -9.96921E36;
        Float32 valid_range 150.0, 350.0;
        Float32 actual_range 182.11667, 322.367;
        String dataset "NCEP Reanalysis Derived Products";
        UInt32 _ChunkSizes 1, 1, 73, 144;
    }
    valid_yr_count {
        String long_name "count of non-missing values used in mean";
        Int16 missing_value 32767;
        Float32 add_offset 0.0;
        Float32 scale_factor 1.0;
    }
    NC_GLOBAL {
        String Conventions "COARDS";
        String title "4x daily NMC reanalysis";
        String description "Data is from NMC initialized reanalysis
(4x/day).  It consists of most variables interpolated to
pressure surfaces from model (sigma) surfaces.";
        String platform "Model";
        String history "Created 2022/02/15 by do4XdayLTMNC4";
        String dataset_title "NCEP-NCAR Reanalysis 1";
        String References "http://www.psl.noaa.gov/data/gridded/data.ncep.reanalysis.html";
        String not_missing_threshold_percent "minimum 3% values input to have non-missing output value";
        String _NCProperties "version=2,netcdf=4.7.0,hdf5=1.10.5,";
    }
}
