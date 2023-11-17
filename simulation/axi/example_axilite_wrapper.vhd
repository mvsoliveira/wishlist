library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.numeric_std.all;
use ieee.std_logic_misc.all;

--library proc_common_base_v5_0;
--use proc_common_base_v5_0.ipif_pkg.all;

library axi_lite_ipif_v3_0_4;
use axi_lite_ipif_v3_0_4.ipif_pkg.all;

entity example_axilite_wrapper is
  generic (

    C_S_AXI_DATA_WIDTH     : integer range 32 to 32        := 32;
    C_S_AXI_ADDR_WIDTH     : integer                       := 32;
    C_S_AXI_MIN_SIZE       : std_logic_vector(31 downto 0) := X"FFFFFFFF";
    C_USE_WSTRB            : integer                       := 0;
    C_DPHASE_TIMEOUT       : integer range 0 to 512        := 8;
    C_ARD_ADDR_RANGE_ARRAY : SLV64_ARRAY_TYPE              :=  -- not used
    (
      X"0000_0000_0000_0000",           -- IP user0 base address
      X"0000_0000_FFFF_FFFF"            -- IP user0 high address
      );

    C_ARD_NUM_CE_ARRAY : INTEGER_ARRAY_TYPE :=  -- not used
    (0 => 1);
    C_FAMILY           : string             := "virtex6"
    );
  port (

    --System signals
    S_AXI_ACLK    : in  std_logic;
    S_AXI_ARESETN : in  std_logic;
    S_AXI_AWADDR  : in  std_logic_vector
    (C_S_AXI_ADDR_WIDTH-1 downto 0);
    S_AXI_AWVALID : in  std_logic;
    S_AXI_AWREADY : out std_logic;
    S_AXI_WDATA   : in  std_logic_vector
    (C_S_AXI_DATA_WIDTH-1 downto 0);
    S_AXI_WSTRB   : in  std_logic_vector
    ((C_S_AXI_DATA_WIDTH/8)-1 downto 0);
    S_AXI_WVALID  : in  std_logic;
    S_AXI_WREADY  : out std_logic;
    S_AXI_BRESP   : out std_logic_vector(1 downto 0);
    S_AXI_BVALID  : out std_logic;
    S_AXI_BREADY  : in  std_logic;
    S_AXI_ARADDR  : in  std_logic_vector
    (C_S_AXI_ADDR_WIDTH-1 downto 0);
    S_AXI_ARVALID : in  std_logic;
    S_AXI_ARREADY : out std_logic;
    S_AXI_RDATA   : out std_logic_vector
    (C_S_AXI_DATA_WIDTH-1 downto 0);
    S_AXI_RRESP   : out std_logic_vector(1 downto 0);
    S_AXI_RVALID  : out std_logic;
    S_AXI_RREADY  : in  std_logic

    );

end example_axilite_wrapper;

architecture rtl of example_axilite_wrapper is

  -- IP signals
  signal Bus2IP_Clk    : std_logic;
  signal Bus2IP_Resetn : std_logic;
  signal Bus2IP_Addr   : std_logic_vector((C_S_AXI_ADDR_WIDTH-1) downto 0);
  signal Bus2IP_RNW    : std_logic;
  signal Bus2IP_BE     : std_logic_vector(((C_S_AXI_DATA_WIDTH/8)-1) downto 0);
  signal Bus2IP_CS     : std_logic_vector(((C_ARD_ADDR_RANGE_ARRAY'LENGTH)/2-1) downto 0);
  signal Bus2IP_RdCE   : std_logic_vector((calc_num_ce(C_ARD_NUM_CE_ARRAY)-1) downto 0);
  signal Bus2IP_WrCE   : std_logic_vector((calc_num_ce(C_ARD_NUM_CE_ARRAY)-1) downto 0);
  signal Bus2IP_Data   : std_logic_vector((C_S_AXI_DATA_WIDTH-1) downto 0);
  signal IP2Bus_Data   : std_logic_vector((C_S_AXI_DATA_WIDTH-1) downto 0);
  signal IP2Bus_WrAck  : std_logic;
  signal IP2Bus_RdAck  : std_logic;
  signal IP2Bus_Error  : std_logic;

begin  -- architecture rtl

  axi_lite_ipif_1 : entity axi_lite_ipif_v3_0_4.axi_lite_ipif
    generic map (
      C_S_AXI_DATA_WIDTH     => C_S_AXI_DATA_WIDTH,
      C_S_AXI_ADDR_WIDTH     => C_S_AXI_ADDR_WIDTH,
      C_S_AXI_MIN_SIZE       => C_S_AXI_MIN_SIZE,
      C_ARD_ADDR_RANGE_ARRAY => C_ARD_ADDR_RANGE_ARRAY,
      C_ARD_NUM_CE_ARRAY     => C_ARD_NUM_CE_ARRAY,
      C_USE_WSTRB            => C_USE_WSTRB,
      C_DPHASE_TIMEOUT       => C_DPHASE_TIMEOUT,
      C_FAMILY               => C_FAMILY)
    port map (
      S_AXI_ACLK    => S_AXI_ACLK,
      S_AXI_ARESETN => S_AXI_ARESETN,
      S_AXI_AWADDR  => S_AXI_AWADDR,
      S_AXI_AWVALID => S_AXI_AWVALID,
      S_AXI_AWREADY => S_AXI_AWREADY,
      S_AXI_WDATA   => S_AXI_WDATA,
      S_AXI_WSTRB   => S_AXI_WSTRB,
      S_AXI_WVALID  => S_AXI_WVALID,
      S_AXI_WREADY  => S_AXI_WREADY,
      S_AXI_BRESP   => S_AXI_BRESP,
      S_AXI_BVALID  => S_AXI_BVALID,
      S_AXI_BREADY  => S_AXI_BREADY,
      S_AXI_ARADDR  => S_AXI_ARADDR,
      S_AXI_ARVALID => S_AXI_ARVALID,
      S_AXI_ARREADY => S_AXI_ARREADY,
      S_AXI_RDATA   => S_AXI_RDATA,
      S_AXI_RRESP   => S_AXI_RRESP,
      S_AXI_RVALID  => S_AXI_RVALID,
      S_AXI_RREADY  => S_AXI_RREADY,
      Bus2IP_Clk    => Bus2IP_Clk,
      Bus2IP_Resetn => Bus2IP_Resetn,
      Bus2IP_Addr   => Bus2IP_Addr,
      Bus2IP_RNW    => Bus2IP_RNW,
      Bus2IP_BE     => Bus2IP_BE,
      Bus2IP_CS     => Bus2IP_CS,
      Bus2IP_RdCE   => Bus2IP_RdCE,
      Bus2IP_WrCE   => Bus2IP_WrCE,
      Bus2IP_Data   => Bus2IP_Data,
      IP2Bus_Data   => IP2Bus_Data,
      IP2Bus_WrAck  => IP2Bus_WrAck,
      IP2Bus_RdAck  => IP2Bus_RdAck,
      IP2Bus_Error  => IP2Bus_Error);

end architecture rtl;
