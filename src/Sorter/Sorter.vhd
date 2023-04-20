------------------------------------------------------------------------------
-- Author: Stephan Proß
--
-- Create Date: 03/08/2022 02:46:11 PM
-- Design Name:
-- Module Name: Sorter
-- Project Name: BitSerialCompareSwap
-- Tool Versions: Vivado 2021.2
--
----------------------------------------------------------------------------------

library IEEE;
use IEEE.STD_LOGIC_1164.all;
use IEEE.NUMERIC_STD.all;

library work;
use work.CustomTypes.all;

entity SORTER is
  generic (
    -- Bit-width of words
    W        : integer := 8;
    -- Bit-width of subwords
    SW       : integer := 1;
    -- Number of input words.
    N        : integer := 704;
    -- Number of sorted ouput words.
    M        : integer := 704;
    -- Number of available BRAMs
    NUM_BRAM : integer := 4318
    );
  port (
    -- System clock
    CLK_I            : in  std_logic;
    -- Enable signal
    ENABLE_I         : in  std_logic;
    -- Syncronous reset
    RST_I            : in  std_logic;
    -- Ready-Valid signals for data input.
    DATA_IN_READY_O  : out std_logic;
    DATA_IN_VALID_I  : in  std_logic;
    -- Parallel input of N unsorted w-bit words.
    DATA_I           : in  SLVArray(0 to N - 1)(W - 1 downto 0);
    -- Ready-Valid signals for data output.
    DATA_OUT_READY_I : in  std_logic;
    DATA_OUT_VALID_O : out std_logic;
    -- Parallel ouput of N sorted w-bit words.
    DATA_O           : out SLVArray(0 to M - 1)(W - 1 downto 0)
    );
end entity SORTER;

architecture STRUCTURAL of SORTER is

  -- Number of BRAM blocks required per IO.
  constant BRAM_PER_IO     : integer := (W + 32 - 1) / 32;
  -- Number of available IO ports replacable with BRAM version.
  constant NUM_IO_BRAM     : integer := NUM_BRAM / BRAM_PER_IO;
  -- Number of remaining BRAMS for output deserialization.
  constant NUM_OUTPUT_BRAM : integer := NUM_IO_BRAM - N;


  -- Start signal generated by cycle timer.
  signal start          : std_logic;
  -- Start signal after delay from replication.
  signal start_feedback : std_logic;
  -- Start signal after collective delays from the
  -- entire sorting network.
  signal start_delayed  : std_logic_vector;

  -- Enable signal after delay from replication.
  signal enable_feedback : std_logic;
  -- Enable signal after collective delays from the
  -- entire sorting network.
  signal enable_delayed  : std_logic_vector;

  -- Serial unsorted data.
  signal stream_unsorted : SLVArray(0 to N - 1)(SW - 1 downto 0);
  -- Serial sorted data.
  signal stream_sorted   : SLVArray(0 to M - 1)(SW - 1 downto 0);

begin


  CYCLE_TIMER_1 : entity work.cycle_timer
    generic map (
      W     => W,
      SW    => SW
      )
    port map (
      CLK_I    => CLK_I,
      RST_I    => RST_I,
      ENABLE_I => ENABLE_I,
      START_O  => start
      );

  SERIALIZER : entity work.serializersw_sr
    generic map (
      N  => N,
      W  => W,
      SW => SW
      )
    port map (
      CLK_I      => CLK_I,
      RST_I      => RST_I,
      ENABLE_I   => enable_feedback,
      LOAD       => start_feedback,
      DATA_I     => DATA_I,
      SER_OUTPUT => stream_unsorted
      );


  ODDEVEN_8X8_1 : entity work.ODDEVEN_8X8
    port map (
      CLK_I             => CLK_I,
      RST_I             => RST_I,
      ENABLE_I          => ENABLE_I,
      START_I           => start,
      STREAM_I          => stream_unsorted,
      START_O           => start_delayed,
      START_FEEDBACK_O  => start_feedback,
      ENABLE_O          => enable_delayed,
      ENABLE_FEEDBACK_O => enable_feedback,
      STREAM_O          => stream_sorted);


  DESERIALIZER : entity work.deserializersw_sr
    generic map (
      N  => M,
      W  => W,
      SW => SW
      )
    port map (
      CLK_I    => CLK_I,
      RST_I    => RST_I,
      ENABLE_I => enable_delayed,
      STORE_I  => start_delayed,
      STREAM_I => stream_sorted,
      DATA_O   => DATA_O
      );

end architecture STRUCTURAL;
