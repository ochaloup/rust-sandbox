use solana_program::program_error::ProgramError;
use std::convert::TryInto;


pub enum ChkpCounterInstruction {

    /// Define the type of state stored in accounts
    #[derive(BorshSerialize, BorshDeserialize, Debug)]
    pub struct ChkpCounterAccount {
        /// counter of calls
        pub counter: u32,
    }
}
