#![allow(unused_imports)]

// extern crate proc_macro;
// extern crate syn;
// #[macro_use]
// extern crate quote;

use std::{collections::HashMap};
use proc_macro::{TokenStream};
use quote::{ToTokens, quote};
// use syn::{Ident};
use syn::{Attribute, DeriveInput, parse_macro_input, Path, punctuated::Punctuated, Token};
use syn_unnamed_struct::{Meta};
// use proc_macro2::{Ident, Span};

#[derive(Default)]
struct FieldArgs {
    pub mutate: bool,
    pub signer: bool,
}

#[proc_macro_derive(HelloWorld, attributes(discriminator, account))]
pub fn derive_trait(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input);
    let DeriveInput { ident, attrs, data, .. } = &input;

    let mut output = proc_macro2::TokenStream::new();
    
    let name = ident.clone();
    println!(">>>> name: {:?}", name);
    let expanded = quote! {
        impl HelloWorld for #name {
            fn hello_world() {
                println!("Hello, World! from {}", stringify!(#name));
            }
        }
    };
    output.extend(expanded);
    
    let obj = match data {
        syn::Data::Struct(obj) => obj,
        _ => panic!("Only structs supported in From macro")
    };
    let attributes = obj.fields
        .iter()
        .map(|field| {
            let field_name = field.ident.as_ref().expect("Structs must contain named fields").clone();
            let mut props = FieldArgs::default();
            field.attrs.iter().filter(|a| a.path.is_ident("account")).flat_map(|attr| {
                attr.parse_args_with(<Punctuated<Meta, Token![,]>>::parse_terminated).expect("Could not parse 'from' attribute")
            }).for_each(|meta| {
                match meta {
                    Meta::Path(path) => {
                        match path.to_token_stream().to_string().as_str() {
                            "mut" => {
                                props.mutate = true;
                            },
                            "signer" => {
                                props.signer = true;
                            },
                            _ => panic!("Unrecognised attribute of field {}", field_name.to_string())
                        }
                    },
                    _ => panic!("Attribute for field {} contains urecognized value", field_name.to_string())
                }
            });

            (field_name,props)
        })
        .collect::<Vec<_>>();
    println!(">>>> Struct idents: {:?}", attributes.iter().map(|(i,_)| i).collect::<Vec<_>>());
    let sss = proc_macro2::Ident::new("String",proc_macro2::Span::call_site());
    let quoted_fields = attributes.iter().map(|(name,_)|{
        quote!(#name: #sss)
    })
    .collect::<Vec<_>>();
    let struct_impl = quote! {
        #[derive(Debug)]
        struct OhMyGosh {
            #(#quoted_fields),*
        }
    };
    output.extend(struct_impl);

    // let type_names = attrs.iter().filter(|a| a.path.is_ident("discriminator")).flat_map(|attr| {
    //     attr.parse_args_with(Punctuated::<Path, Token![,]>::parse_terminated).expect("Could not parse 'discriminator' attribute")
    // }).map(|path| {
    //     (path.to_token_stream().to_string(), path)
    // }).collect::<HashMap<String, Path>>();
    // let n = type_names.iter().map(|(k,_)| {k}).collect::<Vec<_>>();
    // ---
    // println!(">>>> struct attributes: {:?}", n);
    // for i in 0..attrs.len() {
    //     if input.attrs[i].path.is_ident("discriminator") {
    //         let discriminator: &Attribute = input.attrs.get(i).unwrap();
    //         if discriminator.tokens.is_empty() {
    //             panic!("Failed to read discriminator data as have no data");
    //         }
    //         let tokens = discriminator.tokens.clone().into_iter();
    //         for data in tokens {
    //             brace_token: syn::braced!(content in input)
    //             let data_str: String = data.to_string();
    //             println!("next token: '{}'", data_str);
    //         }
    //     }
    // }

    let discriminator_attrs = attrs.iter().filter(|a| a.path.is_ident("discriminator"))
        // .flat_map(|attr| {attr.tokens.clone()}).collect::<Vec<_>>();
        .flat_map(|attr| {attr.tokens.clone()}).collect::<Vec<_>>();
    let discriminator_attr = discriminator_attrs.get(0).unwrap();
    let discriminator_impl = quote! {
        impl OhMyGosh {
            const DISCRIMINATOR:[u8;8] = #discriminator_attr;
        }
    };
    output.extend(discriminator_impl);

    output.into()
}


#[cfg(test)]
mod tests {
    #[test]
    fn it_works() {
        assert_eq!(42, 42);
    }
}
