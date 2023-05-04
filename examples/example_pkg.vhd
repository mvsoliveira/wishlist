-- Automatically generated by WhishList - https://github.com/mvsoliveira/wishlist/
-- Package name: example_pkg
-- Description : IPbus address table for the L1Calo gFEX zynq FPGA

library ieee;
use ieee.std_logic_1164.all;

package example_pkg is

-- register data types

subtype example_user_code_pu_fir_sc_tap_subtype is std_logic_vector(33 downto 0);
type example_user_code_pu_fir_sc_tap_array_type is array (3 downto 0) of example_user_code_pu_fir_sc_tap_subtype;
subtype example_pll_lock_subtype is std_logic;

-- status hierarchy data types
        
        
        
        
        
type example_status_record_type is record
    pll_lock : example_pll_lock_subtype;
end record example_status_record_type;

-- control hierarchy data types
        
type example_control_user_code_pu_fir_sc_record_type is record
    tap : example_user_code_pu_fir_sc_tap_array_type;
end record example_control_user_code_pu_fir_sc_record_type;
type example_control_user_code_pu_fir_sc_array_type is array (5 downto 0) of example_control_user_code_pu_fir_sc_record_type;
        
type example_control_user_code_pu_fir_record_type is record
    sc : example_control_user_code_pu_fir_sc_array_type;
end record example_control_user_code_pu_fir_record_type;
        
type example_control_user_code_pu_record_type is record
    fir : example_control_user_code_pu_fir_record_type;
end record example_control_user_code_pu_record_type;
type example_control_user_code_pu_array_type is array (1 downto 0) of example_control_user_code_pu_record_type;
        
type example_control_user_code_record_type is record
    pu : example_control_user_code_pu_array_type;
end record example_control_user_code_record_type;
        
type example_control_record_type is record
    user_code : example_control_user_code_record_type;
end record example_control_record_type;


end package example_pkg;
