-- Automatically generated by WhishList - https://github.com/mvsoliveira/wishlist/
-- package name: L1CaloGfex_pkg
-- description : IPbus address table for the L1Calo gFEX zynq FPGA

package L1CaloGfex_pkg is

-- register data types

subtype L1CaloGfex_CTEST_REG_subtype is std_logic_vector(31 downto 0);
subtype L1CaloGfex_N_BCRD_CTRL_TWR_LNKS_subtype is std_logic_vector(13 downto 0);
type L1CaloGfex_N_BCRD_CTRL_TWR_LNKS_array_type is array (4 downto 0) of L1CaloGfex_N_BCRD_CTRL_TWR_LNKS_subtype;
subtype L1CaloGfex_N_BCRD_CTRL_GLBL_LNKS_subtype is std_logic_vector(6 downto 0);
subtype L1CaloGfex_N_BCRD_CTRL_JET_LNKS_subtype is std_logic_vector(8 downto 0);
subtype L1CaloGfex_N_BCRD_CTRL_test_subtype is std_logic;
subtype L1CaloGfex_GIT_INFO_GIT_HASH_subtype is std_logic_vector(31 downto 0);
subtype L1CaloGfex_DATE_TIME_subtype is std_logic_vector(31 downto 0);
subtype L1CaloGfex_FW_VER_CODE_subtype is std_logic_vector(31 downto 0);

-- status hierarchy data types
    
type L1CaloGfex_N_BCRD_CTRL_status_record_type is record
    TWR_LNKS : L1CaloGfex_N_BCRD_CTRL_TWR_LNKS_array_type;
    GLBL_LNKS : L1CaloGfex_N_BCRD_CTRL_GLBL_LNKS_subtype;
    JET_LNKS : L1CaloGfex_N_BCRD_CTRL_JET_LNKS_subtype;
    test : L1CaloGfex_N_BCRD_CTRL_test_subtype;
end record L1CaloGfex_N_BCRD_CTRL_status_record_type;
    
type L1CaloGfex_GIT_INFO_status_record_type is record
    GIT_HASH : L1CaloGfex_GIT_INFO_GIT_HASH_subtype;
end record L1CaloGfex_GIT_INFO_status_record_type;
type L1CaloGfex_GIT_INFO_status_record_array_type is array (9 downto 0) of L1CaloGfex_GIT_INFO_status_record_type;
    
type L1CaloGfex_status_record_type is record
    CTEST_REG : L1CaloGfex_CTEST_REG_subtype;
    N_BCRD_CTRL : L1CaloGfex_N_BCRD_CTRL_record_type;
    GIT_INFO : L1CaloGfex_GIT_INFO_record_array_type;
    DATE_TIME : L1CaloGfex_DATE_TIME_subtype;
    FW_VER_CODE : L1CaloGfex_FW_VER_CODE_subtype;
end record L1CaloGfex_status_record_type;
    

-- control hierarchy data types
    
type L1CaloGfex_N_BCRD_CTRL_control_record_type is record
    TWR_LNKS : L1CaloGfex_N_BCRD_CTRL_TWR_LNKS_array_type;
    GLBL_LNKS : L1CaloGfex_N_BCRD_CTRL_GLBL_LNKS_subtype;
    JET_LNKS : L1CaloGfex_N_BCRD_CTRL_JET_LNKS_subtype;
end record L1CaloGfex_N_BCRD_CTRL_control_record_type;
    
    
type L1CaloGfex_control_record_type is record
    CTEST_REG : L1CaloGfex_CTEST_REG_subtype;
    N_BCRD_CTRL : L1CaloGfex_N_BCRD_CTRL_record_type;
end record L1CaloGfex_control_record_type;
    


end package L1CaloGfex_pkg;