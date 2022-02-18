use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint::ProgramResult,
    msg,
    program_error::ProgramError,
    pubkey::Pubkey,
    sysvar::{
        clock::Clock, Sysvar,
    },
};
use borsh::{BorshDeserialize, BorshSerialize};

use crate::{
    instructions::{ChkpCounterAccount, parse_instruction, InstructionTypes},
    errors::ChkpCounterError::{InvalidInstruction, AmountOverflow, WrongCounterClientTimestamp}
};

pub struct Processor;
impl Processor {
    pub fn process(
        program_id: &Pubkey,       // Public key of this program
        accounts: &[AccountInfo],  // The PDA account where the data is saved
        instruction_data: &[u8],   // Data passed with the transaction
    ) -> ProgramResult {
        Self::verify_program_owner(program_id, accounts)?;

        let (instruction_type, rest_data) = parse_instruction(instruction_data);
        return match instruction_type {
            InstructionTypes::Counter => Self::process_counter(program_id, accounts, rest_data),
            InstructionTypes::DeletePda => Self::process_delete_data_account(accounts),
            _ => Err(InvalidInstruction.into())
        };
    }

    pub fn verify_program_owner(program_id: &Pubkey, accounts: &[AccountInfo]) -> Result<(),ProgramError> {
        // Iterating accounts (safer than indexing)
        let accounts_iter = &mut accounts.iter();

        // Get the data account
        let data_account = next_account_info(accounts_iter)?;
        msg!("Program id: {}, data account: {}", program_id, data_account.key);
        // The account must be owned by the program in order to modify its data
        if data_account.owner != program_id {
            msg!("Data account is now owned by correct program id");
            return Err(ProgramError::IncorrectProgramId);
        }

        let signer_account = next_account_info(accounts_iter)?;
        // The owner of the data account (i.e., the most probably the program account) has to sign the transaction
        if data_account.owner != signer_account.key || !signer_account.is_signer {
            msg!("Data account owner has to sign the transaction");
            return Err(ProgramError::IllegalOwner);
        }
        Ok(())
    }

    pub fn process_counter(
        _program_id: &Pubkey,
        accounts: &[AccountInfo],
        instruction_data: &[u8],
    ) -> ProgramResult {
        msg!("ChainKeepers counter program running");

        let accounts_iter = &mut accounts.iter();
        let data_account = next_account_info(accounts_iter)?;

        let clock = Clock::get();
        let timestamp = match clock {
            Ok(clock) => clock.unix_timestamp,
            Err(err) => {
                msg!("Error on using Sysvar Clock {}", err);
                -1
            }
        };
        if instruction_data.len() != 8 { // expected i64 data here
            return Err(WrongCounterClientTimestamp.into())
        }
        let timestamp_data_result = instruction_data.try_into();
        let timestamp_data = match timestamp_data_result {
            Err(_) => return Err(WrongCounterClientTimestamp.into()),
            Ok(data) => data
        };

        let mut counter_account = ChkpCounterAccount::try_from_slice(&data_account.data.borrow())?;
        counter_account.counter += 1;
        counter_account.client_timestamp = i64::from_le_bytes(timestamp_data); // all encoding is little endian
        counter_account.timestamp = timestamp;
        counter_account.serialize(&mut &mut data_account.data.borrow_mut()[..])?;

        msg!("Counter increased {} time(s), date: {}, client date: {}", 
            counter_account.counter, counter_account.timestamp, counter_account.client_timestamp);

        Ok(())
    }

    pub fn process_delete_data_account(accounts: &[AccountInfo]) -> ProgramResult {
        msg!("Closing data account");

        let accounts_iter = &mut accounts.iter();
        let data_account = next_account_info(accounts_iter)?;
        let _program_account = next_account_info(accounts_iter)?;
        let transfer_account = next_account_info(accounts_iter)?;

        **transfer_account.try_borrow_mut_lamports()? = transfer_account
            .lamports()
            .checked_add(data_account.lamports())  // data_account.lamports()
            .ok_or(AmountOverflow)?;
        **data_account.try_borrow_mut_lamports()? = 0;
        *data_account.try_borrow_mut_data()? = &mut [];

        Ok(())
    }
}

// Sanity tests
#[cfg(test)]
mod test {
    use super::*;
    use solana_program::clock::Epoch;
    use std::mem;
    use Processor;

    #[test]
    fn test_sanity() {
        let data_pubkey = Pubkey::new_unique();
        let program_pubkey = Pubkey::new_unique();
        let mut lamports = 0;
        let mut data = vec![0; mem::size_of::<u32>() + mem::size_of::<i64>() + mem::size_of::<i64>()];
        let data_account = AccountInfo::new(
            &data_pubkey,
            false,
            true,
            &mut lamports,
            &mut data,
            &program_pubkey,
            false,
            Epoch::default(),
        );
        let program_owner = Pubkey::default();
        let mut lamports_program = 0;
        let mut data_program = vec![];
        let program_account = AccountInfo::new(
            &program_pubkey,
            true,
            true,
            &mut lamports_program,
            &mut data_program,
            &program_owner,
            false,
            Epoch::default(),
        );
        let timestamp_data = vec![4,0,0,0,0,0,0,0]; // little endian

        let accounts = vec![data_account.clone(), program_account.clone()];

        let account = ChkpCounterAccount::try_from_slice(&accounts[0].data.borrow()).unwrap();
        assert_eq!(account.counter, 0);
        assert_eq!(account.timestamp, 0);

        Processor::process_counter(&program_pubkey, &accounts, &timestamp_data).unwrap();
        let account = ChkpCounterAccount::try_from_slice(&accounts[0].data.borrow()).unwrap();
        assert_eq!(account.counter, 1);
        assert_eq!(account.timestamp, -1);

        Processor::process_counter(&program_pubkey, &accounts, &timestamp_data).unwrap();
        let account = ChkpCounterAccount::try_from_slice(&accounts[0].data.borrow()).unwrap();
        assert_eq!(account.counter, 2);
        assert_eq!(account.timestamp, -1);


        let instruction_data = vec![0];
        let error = Processor::process(&program_pubkey, &accounts, &instruction_data);
        assert_eq!(error, Err(InvalidInstruction.into()));

        let mut instruction_data = vec![1];
        instruction_data.extend(timestamp_data);
        Processor::process(&program_pubkey, &accounts, &instruction_data).unwrap();
        let account = ChkpCounterAccount::try_from_slice(&accounts[0].data.borrow()).unwrap();
        assert_eq!(account.counter, 3);
        assert_eq!(account.timestamp, -1);

        let accounts = vec![data_account.clone(), program_account.clone(), program_account.clone()];
        let instruction_data = vec![2];  // delete account insruction
        Processor::process(&program_pubkey, &accounts, &instruction_data).unwrap();
        assert_eq!(accounts[0].lamports(), 0 as u64);
        assert_eq!(&accounts[0].data.take(), &[]);
    }
}