use borsh::{BorshDeserialize, BorshSerialize};

/// Define the type of state stored in accounts
#[derive(BorshSerialize, BorshDeserialize, Debug)]
pub struct ChkpCounterAccount {
    /// counter of calls
    pub counter: u32,
    pub timestamp: i64,
}