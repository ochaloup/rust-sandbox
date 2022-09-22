use anchor_lang::prelude::*;

declare_id!("HyZYMjt8ijqkX6L56Fe2FWm6EQJLLLgxmECU2ZSc5Zrq");

#[program]
pub mod marinade_rs_sdk_test {
    use super::*;

    pub fn initialize(_ctx: Context<Initialize>) -> Result<()> {
        Ok(())
    }

    pub fn call_marinade(_ctx: Context<CallMarinade>) -> Result<()> {
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize {}

#[derive(Accounts)]
pub struct CallMarinade {
// pub struct CallMarinade<'info> {
    // pub puppet: Account<'info, Data>,
    // pub puppet_program: Program<'info, Puppet>,
}
