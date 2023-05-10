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
  port (
    -- System clock
    CLK_I            : in    std_logic;
    -- Enable signal
    ENABLE_I         : in    std_logic;
    -- Syncronous reset
    RST_I            : in    std_logic;
    -- Ready-Valid signals for data input.
    DATA_IN_READY_O  : out   std_logic;
    DATA_IN_VALID_I  : in    std_logic;
    -- Parallel input of N unsorted w-bit words.
    DATA_I           : in    SLVArray(0 to {num_inputs} - 1)({word_width} - 1 downto 0);
    -- Ready-Valid signals for data output.
    DATA_OUT_READY_I : in    std_logic;
    DATA_OUT_VALID_O : out   std_logic;
    -- Parallel ouput of N sorted w-bit words.
    DATA_O           : out   SLVArray(0 to {num_outputs} - 1)({word_width} - 1 downto 0)
  );
end entity SORTER;

architecture STRUCTURAL of SORTER is

  -- Constants set by network generator.
  constant NUM_BRAM                     : integer := {num_bram};
  -- Bit-Width of words
  constant W                            : integer := {word_width};
  -- Length of subwords, i.e. number of bits to be sorted at a time.
  constant SW                           : integer := {subword_width};
  -- Number of inputs
  constant N                            : integer := {num_inputs};
  -- Number of outputs
  constant M                            : integer := {num_outputs};

  -- Number of BRAM blocks required per IO.
  constant BRAM_PER_IO                  : integer := (W + 32 - 1) / 32;
  -- Number of available IO ports replacable with BRAM version.
  constant NUM_IO_BRAM                  : integer := NUM_BRAM / BRAM_PER_IO;
  -- Number of remaining BRAMS for output deserialization.
  constant NUM_OUTPUT_BRAM              : integer := NUM_IO_BRAM - N;

  -- Start signal generated by cycle timer.
  signal start                          : std_logic;
  -- Start signal after delay from replication.
  signal start_feedback                 : std_logic;
  -- Start signal after collective delays from the
  -- entire sorting network.
  constant NUM_START                    : integer := {num_start};
  signal   start_delayed                : std_logic_vector(0 to NUM_START - 1);

  -- Enable signal after delay from replication.
  signal enable_feedback                : std_logic;
  -- Enable signal after collective delays from the
  -- entire sorting network.
  constant NUM_ENABLE                   : integer := 1;
  signal   enable_delayed               : std_logic_vector(0 to NUM_ENABLE - 1);

  -- Serial unsorted data.
  signal stream_unsorted                : SLVArray(0 to N - 1)(SW - 1 downto 0);
  -- Serial sorted data.
  signal stream_sorted                  : SLVArray(0 to M - 1)(SW - 1 downto 0);

  -- Stall signal indicating presence of backpressure at the sorter output.
  -- There is currently no purpose for this signal.
  signal stall                          : std_logic;

  signal s_ready, s_valid               : std_logic;
  signal d_ready, d_valid               : std_logic;
  signal net_enable                     : std_logic;

begin

  s_valid          <= DATA_IN_VALID_I;
  DATA_IN_READY_O  <= s_ready;
  DATA_OUT_VALID_O <= d_valid;
  d_ready          <= DATA_OUT_READY_I;

  CYCLE_TIMER_1 : entity work.cycle_timer
    generic map (
      W  => W,
      SW => SW
    )
    port map (
      CLK_I    => CLK_I,
      RST_I    => RST_I,
      ENABLE_I => ENABLE_I,
      START_O  => start
    );

  SERIALIZER : entity work.serializer_sr
    generic map (
      N  => N,
      W  => W,
      SW => SW
    )
    port map (
      CLK_I          => CLK_I,
      RST_I          => RST_I,
      ENABLE_I       => ENABLE_I,
      NET_ENABLE_O   => net_enable,
      NET_FEEDBACK_I => enable_feedback,
      START_I        => start_feedback,
      VALID_I        => s_valid,
      READY_O        => s_ready,
      DATA_I         => DATA_I,
      STREAM_O       => stream_unsorted
    );

  NETWORK : entity work.{top_name}
    port map (
      CLK_I             => CLK_I,
      RST_I             => RST_I,
      ENABLE_I          => net_enable,
      START_I           => start,
      STREAM_I          => stream_unsorted,
      START_O           => start_delayed,
      START_FEEDBACK_O  => start_feedback,
      ENABLE_O          => enable_delayed,
      ENABLE_FEEDBACK_O => enable_feedback,
      STREAM_O          => stream_sorted
    );

  DESERIALIZER : entity work.deserializer_sr
    generic map (
      N  => N,
      W  => W,
      SW => SW
    )
    port map (
      CLK_I    => CLK_I,
      RST_I    => RST_I,
      ENABLE_I => enable_delayed(0),
      START_I  => start_delayed(0),
      STREAM_I => stream_sorted,
      VALID_O  => d_valid,
      READY_I  => d_ready,
      DATA_O   => DATA_O
    );

end architecture STRUCTURAL;
